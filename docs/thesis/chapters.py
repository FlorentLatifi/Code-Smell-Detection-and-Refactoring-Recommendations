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
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "data" / "results"
FIGURES = Path(__file__).resolve().parent / "figures"

SMELL_SQ = {
    "blob": "Blob",
    "data class": "Data Class",
    "long method": "Long Method",
    "feature envy": "Feature Envy",
}


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

    # Ndarësi i mijësheve në shqip është hapësira, jo presja, dhe zëvendësimi bëhet
    # mbi numrin e vetëm e jo mbi paragrafin: një herë ai u lëshua mbi tërë tekstin
    # dhe i hoqi të gjitha presjet e fjalisë.
    samples = f"{dataset['rows']:,}".replace(",", " ")

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
        f"është i njëanshëm nga mbivlerësimi. "
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
            f"Motori i refaktorimit automatizon {automated} transformime dhe transformoi "
            f"{share:.1%} të vendeve të detektuara; refuzimi trajtohet si rezultat i "
            f"saktë dhe numërohet. "
        )
    third += (
        "Kontributi kryesor nuk është një shifër e vetme, por një hark i plotë e i "
        "riprodhueshëm nga korpusi te rezultati."
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
            "Detektimi automatik i code smells dhe refaktorimi janë studiuar prej më "
            "shumë se dy dekadash. Ky kapitull i ndan burimet në katër grupe: "
            "përkufizimi dhe matja e smells, detektimi me rregulla mbi metrika, "
            "detektimi me mësim të makinës, dhe refaktorimi i automatizuar. Në fund "
            "identifikohet hendeku që ky punim e adreson.",
        ],
    ),
    (
        "2.1",
        "Përkufizimi dhe matja",
        [
            "Katalogun kanonik e jep Fowler (2018): njëzet e katër smells, secili me "
            "refaktorimet që e adresojnë. Përkufizimi "
            "mbetet qëllimisht cilësor: një smell është simptomë, jo gabim, dhe "
            "gjykimi nëse diçka është problem varet nga konteksti.",
            "Matja sasiore u mundësua nga suita e metrikave e Chidamber & Kemerer "
            "(1994), e cila propozoi gjashtë metrika për sistemet e orientuara nga "
            "objektet: WMC, DIT, NOC, CBO, RFC dhe LCOM. Henderson-Sellers "
            "(1996) e rishikoi LCOM-in duke propozuar një variant të normalizuar, "
            "ndërsa Bieman & Kang (1995) prezantuan TCC-në, e cila e mat kohezionin "
            "përmes çifteve të metodave që ndajnë të paktën një fushë. Këto metrika "
            "janë baza mbi të cilën ndërtohet çdo detektim sasior i mëvonshëm.",
            "Sharma & Spinellis (2018) ofrojnë një shqyrtim sistematik të fushës dhe "
            "vërejnë se literatura ka prodhuar përkufizime jokonsistente për smells, "
            "dhe se metodat e detektimit japin rezultate po aq jokonsistente, çka e "
            "bën krahasimin mes mjeteve të vështirë.",
        ],
    ),
    (
        "2.2",
        "Detektimi me rregulla mbi metrika",
        [
            "Marinescu (2004) prezantoi konceptin e strategjive të detektimit: "
            "rregulla që kombinojnë disa metrika me pragje, në vend që të mbështeten "
            "në një metrikë të vetme. Ideja u zhvillua në një katalog të plotë nga "
            "Lanza & Marinescu (2006), ku çdo smell shprehet si kombinim logjik "
            "kushtesh mbi metrika, zakonisht si konjunksion, me pragje të nxjerra "
            "statistikisht nga një korpus prej dyzet e pesë sistemesh Java.",
            "Moha et al. (2010) propozuan DECOR-in, një metodë me gjuhë të "
            "specifikimit për smells, e cila i gjeneron detektorët nga përshkrimet. "
            "Përparësia e këtyre qasjeve është transparenca: kur një detektor ndez, "
            "arsyeja është e lexueshme. Dobësia e tyre është ndjeshmëria ndaj "
            "pragjeve, të cilat janë të vështira për t'u kalibruar përtej korpusit ku "
            "u nxorën.",
            "Palomba et al. (2015) morën një drejtim tjetër me HIST-in, duke i "
            "detektuar smells nga historiku i ndryshimeve në vend që nga një pamje e "
            "vetme e kodit. Kjo e kap një dimension që metrikat statike nuk e shohin, "
            "por kërkon akses në historikun e plotë të depos.",
        ],
    ),
    (
        "2.3",
        "Detektimi me mësim të makinës",
        [
            "Arcelli Fontana et al. (2016) krahasuan gjashtëmbëdhjetë algoritme të "
            "mësimit të makinës mbi katër smells dhe raportuan performancë të lartë "
            "për të gjitha në validimin e kryqëzuar, me J48 dhe Random Forest si më "
            "të mirat. Ky punim u bë referenca kryesore e fushës dhe motivoi një varg "
            "studimesh pasuese.",
            "Megjithatë, Di Nucci et al. (2018) vunë re se në atë studim çdo dataset "
            "përmbante raste të një lloji të vetëm smell-i. E përsëritën eksperimentin "
            "me dataset-e ku bashkëjetojnë disa lloje smells, dhe në këtë konfigurim "
            "më realist teknikat e mësimit të makinës shfaqën kufizime kritike. "
            "Rrjedhimisht, një rezultat i raportuar varet nga mënyra si ndërtohet "
            "bashkësia e vlerësimit, jo vetëm nga algoritmi.",
            "I njëjti kujdes ndaj ndërtimit të të dhënave përcakton njërën nga "
            "zgjedhjet qendrore të këtij punimi: ndarja mes trajnimit dhe testimit "
            "bëhet e grupuar sipas depos, kurrë e rastësishme sipas rreshtave. "
            "Mostrat e së njëjtës depo ndajnë autorë, konvencione dhe shpesh kod të "
            "kopjuar; një ndarje e rastësishme i vendos ato në të dyja anët dhe e "
            "fryn çdo shifër.",
            "Azeem et al. (2019), në një shqyrtim sistematik dhe meta-analizë, gjetën "
            "vetëm pesëmbëdhjetë studime që përdorin mësimin e makinës për detektimin "
            "e smells, nga një bashkësi fillestare prej më shumë se dy mijë punimesh, "
            "dhe përfundojnë se në këtë nënfushë ka ende hapësirë për përmirësim.",
        ],
    ),
    (
        "2.4",
        "E vërteta bazë dhe subjektiviteti",
        [
            "Çdo vlerësim i detektimit kërkon një të vërtetë bazë, dhe këtu literatura "
            "has një problem themelor. Mäntylä & Lassenius (2006) treguan në një "
            "studim empirik se vlerësimi i zhvilluesve për praninë e një smell "
            "është subjektiv dhe se mospajtimi mes tyre është i konsiderueshëm.",
            "Madeyski & Lewowski (2020) e adresuan mungesën e dataset-eve me MLCQ-në, "
            "një bashkësi mostrash Java të etiketuara nga zhvillues profesionistë për "
            "katër smells, me ashpërsi në shkallën none/minor/major/critical. Ky "
            "punim e përdor MLCQ-në si të vërtetë bazë, dhe e trajton mospajtimin mes "
            "rishikuesve si të dhënë që raportohet, jo si zhurmë që pastrohet.",
        ],
    ),
    (
        "2.5",
        "Refaktorimi i automatizuar",
        [
            "Opdyke (1992) e formalizoi refaktorimin në tezën e tij të doktoratës, "
            "duke prezantuar nocionin e parakushteve: një transformim është i sigurt "
            "vetëm nëse kushte të caktuara vërtetohen para aplikimit. Ky nocion "
            "mbetet themeli i çdo motori refaktorimi që pretendon ruajtjen e sjelljes.",
            "Tsantalis & Chatzigeorgiou (2009) propozuan një metodë për identifikimin "
            "e mundësive të Move Method si zgjidhje për Feature Envy: një algoritëm i "
            "bazuar te distanca mes entiteteve dhe klasave nxjerr refaktorime që "
            "ruajnë sjelljen pas kontrollit të një bashkësie parakushtesh, ndërsa "
            "vendimi përfundimtar i mbetet projektuesit.",
            "Murphy-Hill et al. (2012), mbi të dhëna nga më shumë se trembëdhjetë mijë "
            "zhvillues, gjetën se refaktorimi ndërthuret shpesh me ndryshime të tjera "
            "dhe rrallë shënohet në mesazhet e commit-eve, çka e vështirëson matjen e "
            "tij nga historiku. Silva et al. (2016) "
            "pyetën zhvilluesit pse refaktorojnë dhe gjetën se motivet janë kryesisht "
            "praktike, të lidhura me një ndryshim konkret që duhet bërë.",
        ],
    ),
    (
        "2.6",
        "Hendeku",
        [
            "Nga sa më sipër dalin tri vërejtje. E para: qasja me rregulla dhe ajo me "
            "mësim makine rrallë vlerësohen mbi të njëjtën të vërtetë bazë me të "
            "njëjtat metrika, çka e bën krahasimin e drejtpërdrejtë të vështirë. E "
            "dyta: jo çdo punim e deklaron qartë si e ndan bashkësinë e vlerësimit, "
            "ndonëse shifra e raportuar varet pikërisht prej saj. E "
            "treta: detektimi dhe refaktorimi trajtohen zakonisht si probleme të "
            "ndara, ndaj pyetja nëse një smell i detektuar mund edhe të rregullohet "
            "automatikisht mbetet pa përgjigje empirike.",
            "Ky punim i adreson të tria: dy qasjet vlerësohen mbi të njëjtin korpus me "
            "të njëjtin kod pikëzimi, ndarja është e grupuar sipas depos dhe e "
            "deklaruar, dhe motori i refaktorimit raporton se sa nga rastet e "
            "detektuara arrin t'i transformojë vërtet.",
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
            "**Situata ideale.** Për çdo pjesë të kodit, një ekip zhvillimi do të duhej "
            "të dinte nëse ajo mban një problem dizajni, sa i rëndë është ai, dhe cili "
            "transformim e heq pa ndryshuar sjelljen. Ky gjykim do të duhej të ishte i "
            "përsëritshëm dhe i matur kundrejt vlerësimit të zhvilluesve me përvojë.",
            "**Realiteti.** Identifikimi manual nuk shkallëzohet, dhe mjetet ekzistuese "
            "ndalen zakonisht te njoftimi, me pragje të kalibruara gjetiu (Kapitulli 1). "
            "Studimet, nga ana e tyre, rrallë i vënë dy qasjet përballë njëra-tjetrës dhe "
            "nuk e matin nëse një erë e gjetur ndreqet edhe vetë (Nënkapitulli 2.6).",
            "**Fokusi i punës.** Ky punim i krahason dy qasjet e detektimit mbi të njëjtin "
            "korpus të etiketuar nga profesionistë, me ndarje sipas depos dhe me një kod të "
            "përbashkët pikëzimi, dhe mat sa nga vendet e detektuara mund të rishkruhen "
            "automatikisht pa sjellë gabime të reja kompilimi.",
            "Nga ky fokus dalin pyetjet kërkimore dhe objektivat e punimit. Pjesa tjetër e "
            "kapitullit i bën pyetjet të matshme dhe deklaron kufizimet që e formësojnë "
            "atë që mund të pretendohet.",
        ],
    ),
    (
        "3.1",
        "Pyetjet kërkimore",
        [
            "Secila pyetje i përgjigjet njërës nga tri pjesët e sistemit: detektimit me "
            "rregulla, detektimit me mësim makine dhe refaktorimit.",
            ("bullet", "PK1: Sa e saktë është detektimi i bazuar në strategji "
             "metrikash, krahasuar me etiketimet manuale të zhvilluesve "
             "profesionistë?"),
            ("bullet", "PK2: A e përmirëson një model i mësimit të makinës, i "
             "trajnuar mbi të njëjtat metrika, saktësinë e detektimit krahasuar me "
             "pragjet fikse?"),
            ("bullet", "PK3: A i përmirësojnë objektivisht refaktorimet e propozuara "
             "karakteristikat strukturore të kodit, duke ruajtur "
             "kompilueshmërinë dhe sjelljen e tij?"),
            "PK1 e mat problemin e parë të realitetit, pragjet fikse, kundrejt gjykimit "
            "njerëzor. PK2 pyet nëse i njëjti informacion, i përdorur ndryshe, jep më "
            "shumë. PK3 pyet nëse sistemi mund të shkojë përtej njoftimit pa e prishur "
            "kodin.",
        ],
    ),
    (
        "3.2",
        "Qëllimi dhe objektivat",
        [
            "Qëllimi i punimit është projektimi, implementimi dhe vlerësimi empirik i "
            "një sistemi që identifikon code smells në kod burimor Java dhe propozon "
            "refaktorime konkrete e të verifikueshme për t'i adresuar ato. Objektivat "
            "janë:",
            ("bullet", "Të shqyrtohet literatura mbi metrikat e cilësisë së kodit, "
             "strategjitë e detektimit dhe teknikat e refaktorimit."),
            ("bullet", "Të implementohet një motor analize që nxjerr metrika nga kodi "
             "burimor Java në nivel klase dhe metode."),
            ("bullet", "Të implementohet detektimi me rregulla, me strategji të "
             "publikuara dhe pragje të justifikuara nga literatura."),
            ("bullet", "Të trajnohet dhe vlerësohet një klasifikues mbi të dhënat e "
             "etiketuara të MLCQ-së, dhe të krahasohet me rregullat."),
            ("bullet", "Të implementohet një motor refaktorimi që gjeneron transformime "
             "konkrete dhe verifikon efektin e tyre."),
            ("bullet", "Të ndërtohet një ndërfaqe web që i bën rezultatet të "
             "shfrytëzueshme nga zhvilluesi."),
        ],
    ),
    (
        "3.3",
        "Formulimi i matshëm dhe kriteret e suksesit",
        [
            "Detektimi shprehet si klasifikim binar mbi një entitet kodi: një klasë ose "
            "një metodë është ose nuk është shembull i një ere të caktuar. E vërteta "
            "bazë vjen nga rishikuesit profesionistë të MLCQ-së, dhe krahasimi bëhet me "
            "matricën konfuze dhe shifrat që derivohen prej saj.",
            "Refaktorimi nuk është klasifikim, por transformim me parakushte, dhe pyetja "
            "e matshme është «sa shpesh zbatohet pa e prishur kodin». Rezultati i tij "
            "raportohet si numri i vendeve të detektuara, i atyre të transformuara, dhe "
            "shpërndarja e arsyeve pse pjesa tjetër u refuzua. Kriteret e suksesit janë:",
            (
                "bullet",
                "Për PK1: shifra për çdo erë, të prodhuara mbi një korpus të deklaruar "
                "dhe të riprodhueshme me një komandë. Një recall i ulët është përgjigje "
                "e vlefshme; fshehja e tij nuk është.",
            ),
            (
                "bullet",
                "Për PK2: krahasim mostër për mostër me Qasjen A, bashkë me një model "
                "bazë që nuk mëson asgjë, që fitimi të mos ngatërrohet me çekuilibrin.",
            ),
            (
                "bullet",
                "Për PK3: verifikim që çdo rishkrim i aplikuar nuk e prish skedarin, "
                "dhe matje nëse era u hoq. Ruajtja e plotë e sjelljes kërkon "
                "ekzekutimin e testeve të vetë projekteve (Nënkapitulli 3.4).",
            ),
        ],
    ),
    (
        "3.4",
        "Fushëveprimi dhe kufizimet",
        [
            "Punimi kufizohet në gjuhën Java, sepse pjesa dërrmuese e literaturës mbi "
            "metrikat e objekteve dhe datasetet e etiketuara të code smells janë "
            "ndërtuar mbi kod Java. Erërat e vlerësuara janë ato për të cilat ekzistojnë "
            "strategji të publikuara dhe të dhëna të etiketuara. Analiza është statike: "
            "programi nuk ekzekutohet, ndaj karakteristikat që shfaqen vetëm gjatë "
            "ekzekutimit nuk mbulohen.",
            "Dy zgjedhje arkitekturore janë të qëllimshme. E para: analizuesi regjistron "
            "fakte sintaksore dhe nuk zgjidh simbole, ndaj çdo transformim që duhet të "
            "gjejë të gjitha referencat ndaj një emri nuk i provon dot parakushtet e veta, "
            "dhe dy nga pesë transformimet e planifikuara mbeten propozim. Për të njëjtën "
            "arsye Introduce Parameter Object aplikohet vetëm te metodat «private», "
            "thirrjet e të cilave Java-ja i mban brenda skedarit. E dyta: refaktorimi "
            "bëhet me transformime mbi pemën sintaksore dhe jo me gjenerim teksti, sepse "
            "ajo çka aplikohet duhet të jetë e saktë. Nga kjo rrjedh kriteri i motorit: "
            "refuzimi është rezultat i saktë.",
            "Korpusi ruan nga depot që përmend MLCQ-ja vetëm skedarët «.java», pa skedarë "
            "ndërtimi dhe pa varësi, dhe disa depo nuk ishin më të arritshme. Prandaj "
            "çdo rishkrim kontrollohet vetëm me kompilator: nëse kompilon, ose nëse nuk "
            "shton lloj të ri gabimi. Ruajtja e sjelljes, që përmend PK3, **nuk "
            "verifikohet empirikisht në këtë punim**, sepse kërkon ekzekutimin e testeve "
            "të projekteve, çka korpusi nuk e lejon.",
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
VALIDATION_DATE = "18 shtator 2026"
BACKEND_TESTS = 688
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

CHAPTER_4 = [
    (
        None,
        "",
        [
            "Ky kapitull përshkruan çfarë u ndërtua dhe si u mat: sistemin (4.1–4.2), "
            "eksperimentin në radhën e ekzekutimit (4.3–4.9), dhe validimin, "
            "riprodhueshmërinë e etikën (4.10–4.12).",
            "**Qasja e kërkimit.** Kërkimi është sasior dhe eksperimental, me një pjesë "
            "të vetme cilësore. Të tria pyetjet kërkimore pyesin «sa» dhe «a e "
            "përmirëson», dhe përgjigjja e tyre është matje e përsëritshme mbi të "
            "njëjtin korpus: metrikat e kodit, etiketat e rishikuesve të MLCQ-së dhe "
            "verdiktet e kompilatorit. Pjesa cilësore është gjykimi me rubrikë i një "
            "mostre rishkrimesh (Nënkapitulli 4.7), sepse vlera e një rishkrimi për "
            "zhvilluesin nuk matet dot vetëm me kompilim.",
            "**Kufizimet metodologjike.** Tri kufizime të deklaruara te Nënkapitulli 3.4 "
            "e formësojnë gjithë kapitullin: mungesa e zgjidhjes së simboleve, mungesa e "
            "testeve të projekteve dhe mbështetja te një dataset i vetëm. Pesha e tyre "
            "mbi rezultatet diskutohet te Nënkapitulli 6.6.",
        ],
    ),
    (
        "4.1",
        "Arkitektura e sistemit",
        [
            "Sistemi, i quajtur JavaSmell, është ndërtuar si një zinxhir shtresash me "
            "varësi në një drejtim të vetëm: një modul importon vetëm nga shtresat para "
            "tij, kurrë nga ato pas. Kjo e bën secilën shtresë të testueshme veç dhe e "
            "pengon logjikën e detektimit të rrjedhë te shtresa e transportit. Shtresat "
            "dhe rrjedha e të dhënave mes tyre janë:",
            ("figure", str(FIGURES / "arkitektura_e_sistemit.png"),
             "Arkitektura e sistemit dhe rrjedha e të dhënave"),
            ("bullet", "parsing: lexon skedarët «.java» me tree-sitter dhe regjistron "
             "vetëm fakte sintaksore, si deklarimet, thirrjet dhe qasjet në fusha "
             "(emër i thjeshtë, «this.x» ose «marrësi.anëtari»). Nuk zgjidh simbole."),
            ("bullet", "model dhe metrics: struktura të thjeshta të dhënash për klasat, "
             "metodat dhe fushat, dhe metrikat e tyre, të llogaritura me një kalim të "
             "vetëm mbi çdo klasë."),
            ("bullet", "detectors: funksione të pastra që marrin një entitet dhe "
             "pragjet, dhe kthejnë erën bashkë me kushtet e vlerësuara. Çdo prag "
             "numerik rri në një skedar të vetëm."),
            ("bullet", "ml dhe refactor: Qasja B dhe Qasja C. Të dyja përdorin daljen e "
             "detektorëve dhe modelin, por nuk importojnë njëra-tjetrën."),
            ("bullet", "projects: materializon te disku një depo publike të GitHub-ut, "
             "që analiza të mos kërkojë një kopje të shkarkuar më parë."),
            ("bullet", "api: vetëm transport, pra validim, serializim dhe hartëzim "
             "gabimesh, pa logjikë detektimi apo refaktorimi."),
            ("bullet", "frontend: ndërfaqja web, që flet me shërbimin vetëm përmes HTTP."),
            "Për një analizë, projekti lexohet dhe parsohet i tëri, sepse disa metrika "
            "varen nga tipat e tjerë të projektit. Çdo entitet matet, detektorët "
            "vlerësojnë strategjitë, dhe nëse përdoruesi e kërkon, modeli jep verdiktin e "
            "vet mbi të njëjtat metrika. Për çdo erë me transformim të automatizuar, "
            "motori i refaktorimit prodhon një diff të verifikuar. E njëjta rrjedhë "
            "arrihet nga rreshti i komandës dhe nga shërbimi HTTP.",
            "Paketa evaluation dhe skriptet e dosjes scripts/ nuk janë pjesë e rrjedhës "
            "që sheh përdoruesi. Ato i ekzekutojnë të njëjtat shtresa mbi korpusin dhe "
            "shkruajnë rezultatet, ndaj çdo numër i Kapitullit 5 prodhohet nga i njëjti "
            "kod që përdor zhvilluesi, jo nga një kopje e tij.",
        ],
    ),
    (
        "4.2",
        "Teknologjitë e përdorura",
        [
            "Backend-i dhe eksperimentet janë shkruar në Python, ndërfaqja në "
            "TypeScript. Çdo varësi është falas, me licencë të hapur, dhe e fiksuar në "
            "version të saktë, që një rezultat të riprodhohet me versionin që e prodhoi.",
            ("table", "Teknologjitë e përdorura dhe roli i tyre",
             ["Teknologjia", "Versioni", "Roli"], TECHNOLOGIES),
            "tree-sitter jep pemë sintaksore të plotë edhe për kod që nuk kompilon, pa "
            "ndërtuar projektin; scikit-learn ofron ndarjen e grupuar, ansamblet e pemëve "
            "dhe rëndësinë me permutim. Asnjë model gjuhësor dhe asnjë shërbim me pagesë "
            "nuk përdoret në sistem.",
        ],
    ),
    (
        "4.3",
        "Korpusi dhe e vërteta bazë",
        [
            "MLCQ (Madeyski & Lewowski, 2020) përmban rishikime nga zhvillues "
            "profesionistë, por jo kodin: çdo rresht tregon depon, commit-in dhe "
            "entitetin. Kodi u materializua duke shkarkuar çdo depo në commit-in e "
            "saktë të regjistruar.",
            "Depot e zhvendosura u ndoqën vetëm kur commit-i i regjistruar zgjidhej "
            "te vendndodhja e re. SHA-ja e git-it është hash i përmbajtjes, ndaj nëse "
            "ai zgjidhet, pema është provueshëm e njëjta që panë rishikuesit; nëse "
            "nuk zgjidhet, depoja nuk zëvendësohet me hamendje.",
            "Përputhja mes një mostre të MLCQ-së dhe një entiteti të modelit tonë "
            "ankorohet te rangu i rreshtave dhe verifikohet me emrin. Emri i "
            "publikuar i entitetit vjen në katër formate të ndryshme dhe nuk është i "
            "besueshëm si ankorim.",
        ],
    ),
    (
        "4.4",
        "Matja e metrikave",
        [
            "Analizuesi ndërtohet mbi tree-sitter (Brunsfeld et al.), dhe mbi modelin "
            "sintaksor që ai prodhon maten shtatëmbëdhjetë metrika "
            "klase dhe nëntë metrika metode, me një kalim të vetëm për klasë. Ndër to "
            "janë metrikat e Chidamber & Kemerer-it (1994), varianti i normalizuar i "
            "LCOM-it i Henderson-Sellers-it (1996), TCC-ja e Bieman & Kang-ut (1995) "
            "dhe kompleksiteti ciklomatik (McCabe, 1976), i matur si numri i pikave "
            "të vendimit në trupin e metodës plus një. Të gjitha janë te Shtojca 8.3.",
            "Rreshtat e kodit numërohen si rreshta logjikë, sipas dallimit që bën Park "
            "(1992) mes rreshtave fizikë dhe logjikë: rreshtat bosh, komentet dhe "
            "rreshtat me vetëm shenja ndarëse, si «}» ose «});», nuk janë pohime dhe "
            "nuk numërohen.",
            "Metrikat ATFD, CBO, DIT dhe TCC përcaktohen kundrejt tipave të tjerë të "
            "projektit. Prandaj çdo depo analizohet e plotë; një klasë e matur e "
            "izoluar do të raportonte vlera thjesht të gabuara.",
        ],
    ),
    (
        "4.5",
        "Qasja A: detektimi me rregulla",
        [
            "Sistemi zbaton tetë strategji. God Class, Data Class, Feature Envy dhe Brain "
            "Method zbatohen ashtu siç janë publikuar nga Lanza & Marinescu (2006); Large "
            "Class, Long Method dhe Long Parameter List ndjekin përshkrimet e Fowler-it "
            "(2018), dhe Deep Nesting mat thellësinë e ndërfutjes së blloqeve. Kushtet "
            "dhe burimi i secilës jepen te Shtojca 8.1. Çdo prag rri i centralizuar në "
            "një skedar të vetëm dhe çdo numër aty ka citim; një vlerë që nuk i "
            "atribuohet dot një burimi nuk përdoret.",
            "Katër strategji vlerësohen kundrejt MLCQ-së: God Class kundrejt etiketës "
            "«blob», Data Class, Feature Envy dhe Long Method kundrejt etiketave me të "
            "njëjtin emër. Për Blob-in pikëzohet edhe një variant që i bashkon God Class "
            "dhe Large Class, detektorin që mbështetet vetëm te madhësia.",
            "Një detektor nuk kthen boolean, por kushtet që vlerësoi bashkë me vlerat "
            "e matura. Kjo bën të mundura tri gjëra: ndërfaqja shpjegon pse diçka u "
            "shënua, punimi raporton cila klauzolë e mbajti detektimin, dhe ashpërsia "
            "derivohet nga sa larg pragut është matja në vend që të caktohet. Shkalla e "
            "ashpërsisë është ajo e MLCQ-së, ndaj dalja e rregullave krahasohet me "
            "etiketat e njeriut pa asnjë hap hartëzimi.",
        ],
    ),
    (
        "4.6",
        "Qasja B: detektimi me mësim makine",
        [
            "Katër modele vlerësohen: klasifikuesi i shumicës, regresioni logjistik, "
            "Random Forest (Breiman, 2001) dhe Gradient Boosting (Friedman, 2001), "
            "të zbatuar me scikit-learn (Pedregosa et al., 2011). Veçoritë janë të gjitha "
            "metrikat e Nënkapitullit 4.4, jo vetëm ato që përdorin strategjitë.",
            "Klasifikuesi i shumicës, që parashikon gjithmonë «pa erë», raportohet si "
            "model bazë.",
            "Ndarja bëhet me GroupKFold sipas depos, që mostrat e një projekti të mos "
            "jenë njëherësh në trajnim dhe në testim (Nënkapitulli 2.3). Parashikimet "
            "janë jashtë fold-it: çdo mostër parashikohet "
            "saktësisht një herë, nga një model që nuk e ka parë kurrë projektin e "
            "saj. Kjo jep të njëjtën formë që prodhojnë detektorët, ndaj dy qasjet "
            "krahasohen mostër për mostër.",
            "Çekuilibri trajtohet me peshë klase, jo me mbi-mostrim. Mbi-mostrimi do "
            "t'i dyfishonte rreshtat përtej kufirit të fold-it dhe do ta prishte "
            "grupimin. Asnjë ribalancim nuk zbatohet mbi bashkësinë e testimit.",
            "Rëndësia e veçorive matet me permutation importance mbi fold-in e mbajtur "
            "jashtë, sepse rëndësia e papastërtisë së një pylli anon nga veçoritë me "
            "shumë vlera të ndryshme.",
            "Rëndësia me permutim thotë cila metrikë ka peshë mbi tërë korpusin, por jo "
            "pse u shënua një entitet i caktuar. Prandaj çdo verdikt pozitiv i modelit "
            "shpjegohet veç: secila metrikë, një nga një, zëvendësohet me mesoren e "
            "bashkësisë së trajnimit dhe modeli pyetet sërish. Nëse ky zëvendësim i vetëm "
            "e çon probabilitetin nën kufirin e vendimit, 0.5, ajo metrikë e mban vetë "
            "verdiktin, dhe ndërfaqja e shkruan si fjali: «po të ishte CLOC-u tipik, kjo "
            "klasë nuk do të shënohej». Metoda krahason dy parashikime reale të modelit "
            "dhe nuk varet nga lloji i tij. Kufiri i saj është se e sheh një metrikë në "
            "një kohë: kur dy metrika mbajnë të njëjtin informacion, zëvendësimi i "
            "njërës mund të mos lëvizë asgjë dhe rasti del i pashpjeguar. Shpjegimi jepet "
            "jashtë fold-it, si vetë verdiktet.",
            "Në ndërfaqe, modeli i trajnuar lexohet nga disku bashkë me manifestin e tij "
            "dhe pyetet vetëm kur përdoruesi e kërkon. Nëse mungon, shërbimi e thotë me "
            "një kod gabimi të veçantë dhe analiza me rregulla vazhdon.",
        ],
    ),
    (
        "4.7",
        "Qasja C: motori i refaktorimit",
        [
            "Motori automatizon tri transformime të Fowler-it (2018): Extract Method për "
            "Long Method dhe Brain Method, Replace Nested Conditional with Guard Clauses "
            "për Deep Nesting, dhe Introduce Parameter Object për Long Parameter List, "
            "vetëm te metodat «private». Për katër erërat e tjera refaktorimet propozohen "
            "pa u aplikuar (Shtojca 8.4).",
            "Çdo transformim deklaron parakushtet e veta. Nëse ndonjëra prej tyre nuk "
            "provohet nga pema e analizës, transformimi kthen «e paaplikueshme» me "
            "arsyen përkatëse, e cila numërohet si rezultat (Shtojca 8.4). Te Extract "
            "Method, një analizë e rrjedhës së të "
            "dhënave kërkon që blloku i nxjerrë të ketë një dalje të vetme, që asnjë "
            "return, break ose continue të mos dalë prej tij, dhe që çdo variabël që "
            "lexon të jetë e caktuar me siguri.",
            "Rishkrimi bëhet mbi rangje bajtash, sepse tree-sitter i jep pozicionet në "
            "bajta të tekstit UTF-8, dhe aplikohet nga fundi para, që pozicionet e çdo "
            "editimi të mbeten të vlefshme. Dy editime që mbivendosen refuzohen.",
            "Verifikimi bëhet në tri nivele, sepse një skedar i një depoje reale "
            "importon fqinjët e vet dhe shpesh nuk kompilon i vetëm. Së pari kontrollohet "
            "nëse skedari i rishkruar parsohet, pastaj nëse javac, i ekzekutuar para dhe "
            "pas, raporton ndonjë lloj të ri gabimi, dhe së fundi, kur skedari kompilon i "
            "vetëm, nëse kompilon ende. Kompilatori thirret me listë të fiksuar "
            "argumentesh, me kufi kohor dhe në një dosje të përkohshme. Kufiri i izolimit "
            "matet veç mbi një mostër të mbjellë skedarësh: i njëjti rishkrim kompilohet "
            "dy herë, i vetëm dhe me burimet e projektit të vet, dhe krahasohen verdiktet.",
            "Pas verifikimit, çdo entitet i rishkruar matet sërish me të njëjtët "
            "detektorë. Klasa matet e tëra para dhe pas, sepse Extract Method krijon një "
            "metodë të re. Kështu matet nëse era u hoq, sa lëvizi metrika mbi të cilën "
            "ndez detektori, dhe nëse rishkrimi solli një erë që nuk ishte aty.",
            "Kompilimi flet vetëm për gjysmën e përkufizimit të Fowler-it (2018), ruajtjen "
            "e sjelljes; përmirësimi i strukturës gjykohet veç, nga një njeri që lexon një "
            "mostër diff-esh sipas një rubrike të fiksuar me tri përmasa: **sjellja** (e "
            "ruajtur, e paqartë, e ndryshuar), **përfitimi** (përmirëson, asnjanës, "
            "përkeqëson) dhe **pranueshmëria** (ashtu si është, pas një ndreqjeje, e "
            "refuzuar). Mostra është e mbjellë me farë dhe e shtresuar sipas "
            "transformimit, dhe shifra e bashkuar ripeshohet me madhësitë reale të "
            "shtresave. Fleta nuk mban verdiktin e kompilatorit, që ai të mos e ndikojë "
            "gjykimin. Intervalet janë Wilson (1927), sepse përafrimi normal me pak "
            "vëzhgime jep kufij jashtë [0, 1] (Brown et al., 2001). Vlerësuesi është "
            "autori i punimit, çka është kufizim i deklaruar.",
        ],
    ),
    (
        "4.8",
        "Ndërfaqja web dhe API",
        [
            "Shërbimi HTTP ofron njëmbëdhjetë pika hyrjeje. /health jep gjendjen, "
            "/analyze analizon një projekt ose skedar, /metrics jep metrikat e një "
            "entiteti, /source kodin e tij, /browse nënndosjet e një shtegu dhe "
            "/projects/github importon një depo publike. Pesë të tjera janë nën "
            "/refactor: pamja paraprake e një rishkrimi (preview), diff-i i të gjitha "
            "rishkrimeve të verifikuara (patch, edhe si rrjedhë progresi), pyetja nëse "
            "shkrimi lejohet (tree) dhe shkrimi në disk (apply). Çdo pikë e validon "
            "kërkesën, thërret të njëjtat funksione si rreshti i komandës dhe e kthen "
            "përgjigjen si JSON.",
            "Aplikacioni ka një përdorues dhe dëgjon vetëm në localhost, ndaj rreziqet "
            "që mbrohen nuk janë autentikimi, por shtegu dhe burimet. Shtegu që dërgon "
            "përdoruesi kanonizohet dhe pranohet vetëm nëse bie brenda një rrënje të "
            "lejuar, edhe pasi ndiqen lidhjet simbolike; rrënjët janë dosja e zgjedhur "
            "dhe ajo e depove të importuara. Një analizë ka kufij për numrin e "
            "skedarëve, madhësinë totale dhe kohën. Gabimet kthehen me mesazh dhe kod, "
            "pa gjurmë të brendshme dhe pa shtigje absolute. Meqë çdo faqe që hap "
            "përdoruesi e arrin localhost-in përmes shfletuesit të tij, çdo kërkesë kalon "
            "një roje: pranohen vetëm emra lokalë te koka Host, që e ndal DNS rebinding, "
            "asnjë POST nga një origjinë e huaj, dhe ndërfaqja nuk lejohet të mbështillet "
            "në një faqe tjetër. /source lexon vetëm skedarë «.java».",
            "Importi nga GitHub shkarkon arkivin e një depoje publike dhe shkruan vetëm "
            "anëtarët «.java», me kufij madhësie dhe me çdo shteg të kontrolluar se bie "
            "brenda dosjes së synuar; importohen vetëm depo publike.",
            "Shkrimi në disk është i vetmi veprim që ndryshon kodin e autorit, ndaj "
            "kërkon një konfirmim të qartë në kërkesë, një depo git pa ndryshime të "
            "pakomituara, dhe skedarë që git-i i ndjek. Vetëm atëherë një komandë e "
            "vetme, «git restore», e kthen gjithçka; nëse një kusht nuk plotësohet, "
            "shkrimi refuzohet me arsyen përkatëse. Shkruhen vetëm rishkrimet që kaluan "
            "verifikimin.",
            "Ndërfaqja është aplikacion React me TypeScript, e ndërtuar një herë dhe e "
            "shërbyer nga i njëjti proces si API-ja. Projekti zgjidhet duke "
            "shfletuar dosjet brenda rrënjëve të lejuara, ose duke importuar një depo, "
            "dhe përdoruesi, sipas dëshirës, kërkon edhe verdiktin e modelit. Paneli "
            "tregon përmbledhjen sipas erës, krahasimin e dy qasjeve dhe gjetjet "
            "sipas skedarit. Për secilën gjetje shfaqen kushtet me vlerat e "
            "matura, shpjegimi i modelit, dhe diff-i i rishkrimit ose arsyeja e "
            "refuzimit në gjuhë të kuptueshme. Pas shkrimit në disk, ndërfaqja tregon "
            "cilat erëra u hoqën dhe cilat lindën.",
        ],
    ),
    (
        "4.9",
        "Matja e performancës",
        [
            "Një mostër quhet pozitive kur ashpërsia e agreguar e rishikuesve është mbi "
            "«none». Agregimi parësor është mesatarja e rishikimeve; maksimumi, "
            "minimumi dhe unanimiteti raportohen si analizë ndjeshmërie, sepse "
            "rishikuesit e MLCQ-së nuk pajtohen me njëri-tjetrin në një të katërtën e "
            "mostrave dhe një shifër e vetme do ta fshihte atë mospajtim.",
            "Mbi këtë përkufizim maten precizioni, recall-i dhe F1-i, bashkë me "
            "koeficientin e korrelacionit të Matthews-it (Matthews, 1975), i cili i "
            "përfshin të katër qelizat e matricës konfuze. Kur shumica e etiketave janë "
            "negative, kjo veti është vendimtare: një detektor që nuk ndez "
            "kurrë del i papërcaktuar këtu, ndërsa saktësia e përgjithshme do t'i jepte "
            "shifër të lartë. Recall-i raportohet edhe i ndarë sipas ashpërsisë që "
            "caktuan rishikuesit.",
            "Pajtimi mes dy qasjeve matet me koeficientin kappa (Cohen, 1960), sepse kur "
            f"{_negative_share()} e etiketave janë negative, dy detektorë që ndezin rrallë "
            "pajtohen shumë vetëm nga rastësia. Raportohen edhe të katër qelizat, "
            "bashkimi i dy qasjeve (mostra shënohet nëse e shënon njëra) dhe prerja e "
            "tyre (nëse e shënojnë të dyja).",
            "Pasiguria e shifrave matet me intervale besimi bootstrap, ku rimostrohen "
            "depo të plota e jo mostra të veçanta, që një projekt të mos ndahet. Pajtimi mes "
            "vetë rishikuesve të MLCQ-së matet mbi çdo çift rishikimesh të së njëjtës "
            "mostër, dhe jep tavanin kundrejt të cilit lexohen shifrat e detektorëve.",
            "Motori i refaktorimit nuk matet me këto shifra. Për të numërohen vendet e "
            "detektuara, ato të transformuara dhe ato të refuzuara sipas arsyes, plus "
            "verdikti i verifikimit për secilin rishkrim.",
            "Si krahasim i jashtëm, i njëjti vlerësim i zbatohet PMD-së (PMD Team, 2026), "
            "version 7.27.0, rregullat GodClass dhe DataClass të të cilit zbatojnë "
            "strategjitë e Lanza & Marinescu (2006). PMD ekzekutohet pa iu prekur "
            "pragjet dhe pikëzohet njësoj si Qasja A; një "
            "shkelje përputhet me entitetin sipas emrit të klasës dhe të metodës. PMD "
            "analizon një skedar në një kohë, ndaj ATFD-në e llogarit vetëm brenda "
            "skedarit, handikap që e favorizon këtë punim; dhe nuk ka rregull për Feature "
            "Envy.",
        ],
    ),
    (
        "4.10",
        "Validimi i sistemit",
        [
            "Sistemi validohet në katër nivele, dhe asnjë ndryshim nuk quhet i "
            "përfunduar pa i kaluar të gjitha:",
            ("bullet", "Testet e backend-it me pytest. Vlerat e pritura derivohen me dorë "
             "nga fiksturat, me derivimin në koment, dhe jo nga dalja aktuale e kodit. Çdo "
             "detektor ka një rast pozitiv, një rast që i plotëson disa kushte por jo të "
             "gjitha, dhe një rast kufitar (ndërfaqe, enum, klasë bosh). Çdo transformim "
             "testohet që aplikohet saktë, që refuzon kur nuk është i sigurt, dhe që dalja "
             "kompilon."),
            ("bullet", "Testet e ndërfaqes me Vitest, dhe testet end-to-end me "
             "Playwright, të cilat nisin të dy shërbimet dhe e përdorin aplikacionin si "
             "përdorues; një pjesë e tyre kontrollon aksesueshmërinë me axe-core."),
            ("bullet", "Analiza statike e kodit: Ruff për stilin dhe mypy në modalitet "
             "strikt, që mbulon edhe skriptet e eksperimenteve, sepse ato prodhojnë "
             "numrat e punimit."),
            ("bullet", "Integrimi i vazhdueshëm: çdo commit ekzekuton pesë punë të "
             "pavarura, për backend-in, ndërfaqen, testet end-to-end, mjetet e Java-s dhe "
             "kontrollet e këtij dokumenti (citimet, formati dhe tabela e riprodhimit)."),
            "Rregulli kryesor i testimit është se asnjë prag, metrikë apo detektor nuk "
            "ndryshohet që të kalojë një test. Kur kodi dhe testi nuk pajtohen, gjendet "
            "më parë cili prej tyre është i gabuar. Në verifikimin e fundit, më "
            f"{VALIDATION_DATE}, kaluan {BACKEND_TESTS} teste të backend-it, me mbulim "
            f"{COVERAGE} të kodit, dhe {FRONTEND_TESTS} teste të ndërfaqes.",
        ],
    ),
    (
        "4.11",
        "Riprodhueshmëria",
        [
            "Çdo numër i raportuar në Kapitullin 5 prodhohet nga një skript dhe "
            "shkruhet si CSV ose JSON që komitohet. Farat e rastësisë janë të "
            "fiksuara, versionet e varësive të pinuara, dhe mjedisi i regjistruar në "
            "çdo skedar rezultati.",
            "Kalimi i shtrenjtë mbi korpusin, 56 minuta për 690 mijë skedarë në matjen "
            "e fundit, bëhet një herë dhe prodhon një tabelë veçorish që komitohet. "
            "Pragjet nuk hyjnë në atë kalim, ndaj analiza e ndjeshmërisë rirendit "
            "detektorët mbi rreshtat e ruajtur në sekonda. Pa këtë ndarje, një fshirje "
            "me njëzet konfigurime do të kushtonte mbi tetëmbëdhjetë orë dhe nuk do të "
            "bëhej. Radha e plotë e skripteve jepet te Shtojca 8.5.",
        ],
    ),
    (
        "4.12",
        "Konsideratat etike",
        [
            "Punimi nuk mbledh të dhëna nga njerëz, ndaj pëlqimi i informuar dhe "
            "konfidencialiteti, që kërkohen kur mblidhen të tilla, nuk zbatohen këtu. "
            "Të gjitha të dhënat që përdor janë "
            "publike: gjykimet e dataset-it MLCQ, të mbledhura dhe të publikuara nga "
            "autorët e tij (Madeyski & Lewowski, 2020), dhe kodi i depove Java me burim "
            "të hapur të cilave u referohen mostrat.",
            "Kodi i këtyre depove përdoret vetëm si objekt matjeje. Ai nuk ekzekutohet "
            "kurrë: analiza e lexon si tekst, dhe verifikimi e kompilon me javac pa e "
            "nisur. Korpusi nuk shpërndahet bashkë me punimin, sepse mbahet jashtë depos "
            "së kodit; kush do t'i riprodhojë rezultatet e shkarkon nga burimet origjinale "
            "me skriptin e parë të Shtojcës 8.5.",
            "Rezultatet negative raportohen njësoj si ato pozitive, që numrat e "
            "Kapitullit 5 të lexohen si matje dhe jo si argument.",
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
        f"{regressions} rishkrime nga {total} e përmbysin verdiktin në drejtimin e "
        "kundërt dhe e kufizojnë pretendimin"
    )


def _blob_recall_limits() -> list:
    """Dy kufizimet që dalin nga Shtojca 8.11, të lexuara nga i njëjti skedar.

    Të shtypura me dorë do të ishin dy pohime numerike brenda kapitullit të
    fundit që lexon komisioni, dhe pikërisht ashtu rrëshqiti Kapitulli 6 një
    herë (VD-73). Nëse analiza mungon, paragrafët nuk ekzistojnë fare.
    """
    data = _load_if_present("blob_recall.json")
    if data is None:
        return []

    strategy = data["per_variant"]["strategy"]
    best = max(float(value) for value in strategy["separation"].values())

    # Numrat e rasteve janë te Shtojca 8.11; këtu jepet vetëm pasoja e tyre, që
    # e njëjta fjali të mos lexohet dy herë (VD-128).
    return [
        "Recall-i i Blob-it ka dy tavane që nuk varen nga pragjet (Shtojca 8.11). I "
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
        "klauzolat (Shtojca 8.8). Humbja e tyre nuk zgjidhet pra duke lëvizur një "
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
    """Ku ndihmoi kalibrimi jashtë fold-it, nga të dhënat e Shtojcës 8.6."""
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
        "**Qasja B.** Modelet e tejkalojnë qasjen me rregulla te çdo erë, dhe meqë "
        "klasifikuesi i shumicës nuk ndez kurrë, fitimi nuk vjen nga çekuilibri i "
        "klasave. I njëjti informacion, i lexuar pa kufij të fiksuar paraprakisht, jep "
        "më shumë: strategjive nuk u mungojnë metrikat, u mungon vendi i duhur ku t'i "
        "presin.",
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
        paragraphs.append(
            "Verdikti i izoluar është më i rreptë se vetë rishkrimi. Brenda projektit të "
            "vet (Nënkapitulli 5.4), shumica e rasteve «pa gabim të ri» kompilojnë "
            "plotësisht, ndaj gabimet e tyre të mëparshme i detyroheshin mungesës së "
            "fqinjëve dhe jo transformimit. Përmbysja e vetme, te Ambari, shton gabime "
            "vetëm sepse tipi që kalon te nënshkrimi i metodës së nxjerrë mban anotacione "
            "nga një bibliotekë që korpusi nuk e ka. Toleranca «pa lloj të ri gabimi» "
            "mbetet dëshmi e përdorshme ku kompilimi i plotë nuk arrihet, por jo garanci."
        )
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
            f"Erërat e reja janë më shpesh {top}, dhe shkaku është i drejtpërdrejtë: "
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
        "të CODEBEAT-it si veçori. Në konfigurimin e tyre DS1 një mostër është "
        "pozitive kur ashpërsia e saj e agreguar është mbi «none», i njëjti përkufizim "
        "që përdor ky punim. Tabela vë përballë MCC-në e të dy qasjeve këtu me mesoren "
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
        "Te rregullat, rezultati përputhet me vërejtjen e Nënkapitullit 2.2 se pragjet "
        "e nxjerra nga një korpus nuk transferohen lehtë në një tjetër: strategjitë e "
        "Lanza & Marinescu (2006) ruajnë precizion të lartë mbi MLCQ, por humbin "
        "shumicën e rasteve. PMD-ja, që zbaton të njëjtat strategji me pragjet e veta, "
        "nuk del më mirë në asnjë krahasim (Shtojca 8.7), ndaj recall-i i ulët nuk "
        "është defekt i zbatimit tonë. Te refaktorimi, motori ndjek parimin e Opdyke "
        "(1992): transformimi aplikohet vetëm kur parakushtet provohen. Tsantalis & "
        "Chatzigeorgiou (2009) ia lënë vendimin përfundimtar projektuesit; ky punim e "
        "aplikon rishkrimin, por vetëm pas verifikimit me kompilator dhe vetëm aty ku "
        "kthimi është një komandë."
    )
    return paragraphs


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
        "të njëjtat metrika e ngre MCC-në te të katër erërat: brezi kalon nga "
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
        "mirë nga fshirja, dallimi te Long Method nuk ndahet më nga zeroja (Shtojca "
        "8.10). Përparësia vlen pra përgjithësisht, jo pikërisht te era ku rregulli "
        "punonte tashmë më mirë.",
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
                "duke e mbivlerësuar sistematikisht (Shtojca 8.9). "
                f"{_calibration_verdict()}, dhe {_folds_disagree()}; një prag «optimal» "
                "që ndryshon me pjesën e korpusit që shihet është veti e bashkësisë, jo "
                "e gjuhës (Shtojca 8.6).",
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
                "tij më të sigurt. Rishkrimi automatik mund t'i besohet mjetit për rreth "
                "një në pesë vende, me kusht që ai të refuzojë çdo gjë që nuk e provon "
                "dhe ta masë atë që ndodh pas rishkrimit.",
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
                "ndryshime në gjithë projektin mbeten te zhvilluesi. Po ashtu, niveli i "
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
# Analizat që nuk i përgjigjen drejtpërdrejt një pyetjeje kërkimore. Rregulli i UBT-së
# e kufizon punimin në 8 deri 10 mijë fjalë pa shtojca, dhe vetëm Kapitulli 5 kishte
# 5 553 fjalë tekst me to brenda. Zhvendosen te shtojcat të plota, pa u shkurtuar
# asnjë fjali (VD-113).
SECONDARY_RESULTS = ("5.5", "5.6", "5.7", "5.8", "5.9", "5.10")
FIRST_APPENDIX_FOR_RESULTS = 6


def chapter_5() -> list:
    """Rezultatet që u përgjigjen pyetjeve kërkimore, 5.1 deri 5.4."""
    return [section for section in _results_sections() if section[0] not in SECONDARY_RESULTS]


def secondary_results() -> list:
    """Analizat dytësore të rezultateve, të rinumëruara si Shtojcat 8.6 deri 8.11."""
    moved = [section for section in _results_sections() if section[0] in SECONDARY_RESULTS]
    return [
        (f"8.{FIRST_APPENDIX_FOR_RESULTS + offset}", title, paragraphs)
        for offset, (_, title, paragraphs) in enumerate(moved)
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
                "Nënkapitujt 5.1 deri 5.4 u përgjigjen pyetjeve kërkimore sipas radhës së "
                "tyre. Analizat dytësore, që u japin kontekst këtyre përgjigjeve pa iu "
                "përgjigjur vetë ndonjë pyetjeje, janë te Shtojcat 8.6 deri 8.11.",
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
                "Pragjet e përdorura janë ato të botuara (Shtojca 8.2), dhe pyetja e "
                "natyrshme është sa varet rezultati prej tyre. Secili prag u zhvendos veç, mes gjysmës dhe dyfishit të vlerës "
                "së vet, me të tjerët të mbajtur fiks.",
                ("table", "Sa lëviz MCC-ja kur zhvendoset një prag",
                 ["Erë", "Pragu", "Te vlera e botuar", "Brezi", "Amplituda"], sweep_rows),
                ("figure", str(FIGURES / "ndjeshmeria_e_pragjeve.png"),
                 "Ndjeshmëria e MCC-së ndaj zhvendosjes së pragjeve"),
                "Ndarja është e qartë. Për Blob dhe Data Class rezultati mezi lëviz, "
                "pra shifrat e raportuara për to flasin për kodin. Për Long Method dhe "
                "Feature Envy amplituda është e madhe, dhe kjo do të thotë se shifra e "
                "raportuar flet po aq për pragun sa për kodin — vërejtje që duhet mbajtur "
                "parasysh sa herë krahasohen mjete të ndryshme detektimi.",
                "Te Long Method pragu i botuar rezulton konservativ për këtë korpus: "
                "ulja e tij e rrit ndjeshëm recall-in me kosto të vogël precizioni, "
                "çka sugjeron se rishikuesit e MLCQ-së e quajnë një metodë të gjatë më "
                "herët se sa e vendos pragu.",
                "Te Feature Envy vërehet diçka më e veçantë. Klauzola që kërkon që "
                "numri i klasave-burim të jetë i vogël, kur relaksohet, i përmirëson "
                "njëkohësisht edhe precizionin edhe recall-in. Një kufizim që heq "
                "pozitivë të vërtetë pa hequr të rremë nuk po e ndan sinjalin nga "
                "zhurma; pra ajo klauzolë, të paktën mbi këtë korpus, nuk e bën punën "
                "për të cilën është vendosur.",
                "Këto vlera nuk adoptohen: një prag i zgjedhur sepse jep shifrën më të mirë "
                "mbi bashkësinë e vlerësimit do të matte sa mirë u zgjodh pragu, jo sa mirë "
                "funksionon detektimi. Kalibrimi i ndershëm kërkon bashkësi të ndara, dhe "
                "kjo bëhet më poshtë.",
                *_calibration_paragraphs(),
            ],
        ),
        (
            "5.6",
            "Krahasimi me një mjet ekzistues",
            [
                "Kapitulli 5 i vë dy qasjet e këtij punimi përballë "
                "njëra-tjetrës. Ky i vë përballë një mjeti që zhvilluesi e instalon "
                "sot, sepse pyetja nuk është vetëm cila prej të dyjave është më e "
                "mirë, por a ia vlen ndonjëra.",
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
            f" Te {'një' if tied == 1 else tied} prej tyre intervali e përmban zeron, "
            "pra dy anët nuk dallohen mbi këtë dëshmi."
        )
    )
    if theirs and not ours:
        return (
            f"Nga {answered} krahasimet me përgjigje, PMD del përpara te {theirs} dhe "
            "detektorët e këtij punimi te asnjëri. Ky është rezultat negativ dhe "
            "raportohet si i tillë." + ties
        )
    if ours and not theirs:
        return (
            f"Nga {answered} krahasimet me përgjigje, detektorët e këtij punimi dalin "
            f"përpara te {ours} dhe PMD te asnjëri." + ties
        )
    if not ours and not theirs:
        return (
            f"Asnjë nga {answered} krahasimet nuk jep ndryshim që e mban riterheqja: "
            "mbi këtë korpus dy anët nuk dallohen."
        )
    return (
        f"Rezultati ndahet: nga {answered} krahasimet me përgjigje, detektorët e këtij "
        f"punimi dalin përpara te {ours} dhe PMD te {theirs}." + ties
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
         ["Era", "Mostra", "MCC i PMD-së", "MCC ynë", "Ndryshimi, IB 95%"], rows),  # fmt: skip
        _pmd_balance(data),
        "Feature Envy nuk ka rresht krahasimi sepse PMD nuk ka rregull për të; "
        "LawOfDemeter, më i afërti, mat zinxhirë mesazhesh dhe nuk është matje e "
        "Feature Envy-së. Mungesa nuk është vetëm e PMD-së: as DesigniteJava nuk e "
        "përfshin mes erërave që dokumenton. JDeodorant e zbulon, sepse ndërtohet mbi "
        "identifikimin e mundësive për Move Method (Tsantalis & Chatzigeorgiou, 2009), "
        "por është shtojcë e mjedisit të zhvillimit dhe varianti i tij në rresht "
        "komande nuk mban licencë. Pra erës që literatura e trajton më shpesh si "
        "objektiv refaktorimi i mungon mbështetja në mjetet e lira të përhapura.",
        "Krahasimi e favorizon këtë punim në drejtimin e deklaruar te Nënkapitulli 4.9, "
        "sepse PMD e llogarit ATFD-në vetëm brenda një skedari. Heqja e handikapit do "
        "të kërkonte ndërtimin e çdo depoje në commit-in e vet historik, çka korpusi "
        "nuk e lejon (Nënkapitulli 6.6).",
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
            f"Nga ekzekutimi, {files} dhe {repos}. Këto numërohen këtu dhe nuk lexohen "
            "si «PMD nuk gjeti asgjë»: dështimi dhe mosgjetja janë pohime të kundërta. "
            "Mostrat e atyre depove dalin nga tabela e mësipërme, dhe dalin nga të dyja "
            "kolonat njësoj, ndaj dy anët mbeten të krahasueshme. Emëruesi që mbetet "
            f"është ai i tabelës; Qasja A vlerësoi {total} mostra, dhe krahasimi mbulon "
            "ato që u përpunuan."
        )
    recovered = len(data.get("reports_recovered", []))
    if recovered:
        which = (
            "Për një depo raporti i PMD-së doli"
            if recovered == 1
            else f"Për {recovered} depo raportet e PMD-së dolën"
        )
        paragraphs.append(
            f"{which} XML i pavlefshëm — një defekt i njohur i renderuesit të tij kur "
            "një skedar dështon — dhe u lexua me një rrugë rikuperimi që prodhon të "
            "njëjtat çelësa. Pa të, ato do të hynin në tabelë sikur PMD të mos kishte "
            "gjetur asgjë."
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

    paragraphs: list = [
        f"Çdo shifër e Kapitullit 5 është një vlerësim i vetëm mbi një korpus të "
        f"caktuar. Për të matur sa varet ajo nga korpusi, çdo tregues u riprodhua me "
        f"bootstrap mbi {intervals['resamples']} rimostrime, duke rimostruar "
        f"**depo** e jo rreshta, për arsyen që e bën edhe ndarjen e trajnimit të "
        f"grupuar (Nënkapitulli 2.3): rimostrimi i rreshtave do të jepte intervale "
        f"artificialisht të ngushta.",
        ("table", "Intervale besimi 95% për MCC-në",
         ["Erë", "A: rregullat", "B: modeli", "B − A", "E kalon zeron"], rows),
        ("figure", str(FIGURES / "intervalet_e_besimit.png"),
         "MCC me interval besimi 95% për të dyja qasjet"),
        "Përparësia e Qasjes B ndaj Qasjes A e kalon zeron te të katër erërat, pra nuk "
        "është artefakt i korpusit. Por intervalet janë të gjera — për Feature Envy-n "
        "gjerësia i kalon njëzet e pesë pikët — prandaj renditja e "
        "erërave mes tyre nuk qëndron: dallimi mes Data Class-it dhe Blob-it, për "
        "shembull, humbet brenda tyre.",
        "Krahasimi ndryshon kur Qasjes A i jepet pragu i saj më i mirë nga fshirja e "
        "Shtojcës 8.6, çka është krahasimi më bujar që mund t'i bëhet:",
        ("table", "B − A kur rregullat marrin pragun e tyre më të mirë",
         ["Erë", "Pragu i zhvendosur", "B − A", "E kalon zeron", "Shenja e ruajtur"],
         swept_rows),
        "Për tri erërat e para përparësia mbetet. Për Long Method-in ajo zhduket: "
        f"intervali e përfshin zeron dhe shenja ruhet vetëm në {_crossing_share(intervals)} "
        "të rimostrimeve. "
        "Pra pretendimi «modeli e tejkalon rregullin» qëndron përgjithësisht, por jo "
        "për erën ku rregulli tashmë punonte më mirë, sapo atij rregulli i lejohet të "
        "kalibrohet. Ky është kufizimi i vetëm i rëndësishëm i krahasimit A↔B.",
    ]

    if ceiling is None:
        return [("5.9", "Sa peshë mban një shifër e vetme", paragraphs)]

    ceiling_rows = [
        [
            SMELL_SQ[smell],
            f"{data['mcc']:.3f}",
            f"{data['accuracy']:.3f}",
            f"{data['pairs']:,}".replace(",", " "),
        ]
        for smell, data in sorted(ceiling["per_smell"].items())
    ]
    best = max(data["mcc"] for data in ceiling["per_smell"].values())

    paragraphs += [
        "Mbetet pyetja e dytë: kundrejt çfarë etikete maten këto shifra. Etiketa është "
        "ndërtuar duke bashkuar rishikime njerëzore, dhe ata rishikues nuk pajtohen me "
        "njëri-tjetrin. Tabela më poshtë e mat atë mospajtim me të njëjtin tregues dhe "
        "të njëjtin kod: një rishikues merret si e vërtetë, tjetri si parashikim, dhe "
        "çifti kalon nëpër të njëjtën matricë konfuze.",
        ("table", "Sa pajtohen rishikuesit me njëri-tjetrin",
         ["Erë", "MCC mes rishikuesve", "Saktësia", "Çifte"], ceiling_rows),
        f"Asnjë erë nuk e kalon {best:.3f}. Kjo nuk do të thotë se sistemi i tejkalon "
        "njerëzit: shifrat e kapitullit maten kundrejt etiketës së agreguar, e cila e "
        "heq një pjesë të zhurmës së një individi, ndaj të dy numrat nuk vendosen në "
        "një renditje. Ajo që tregon është sa e vështirë është vetë detyra: kur ekspertët "
        "ndahen kaq shumë, një pjesë e gabimit mbetet te paqartësia e erës, sido që të "
        "ndërtohet detektori, dhe çdo shifër e Kapitullit 5 duhet lexuar mbi këtë sfond.",
    ]

    return [("5.9", "Sa peshë mban një shifër e vetme", paragraphs)]


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
        f"Kalibrimi u bë me {data['folds']} folde të ndara sipas depos, si te Qasja B. "
        f"Për secilin fold pragu u zgjodh duke parë vetëm foldet e trajnimit dhe u "
        f"pikëzua mbi foldin e mbajtur jashtë; parashikimet u bashkuan dhe u pikëzuan "
        f"një herë, ndaj shifra është jashtë-fold-it në të njëjtin kuptim me atë të "
        f"modeleve.",
        ("table", "Rregullat me pragje të kalibruara, të pikëzuara jashtë fold-it",
         ["Erë", "E botuar", "E kalibruar", "Recall", "Precizion", "Vlerat e zgjedhura"],
         rows),
        "Rezultati ndahet në dy pjesë. Për Feature Envy kalibrimi jep fitimin më të "
        "madh dhe më të besueshmin: **të pesë foldet zgjodhën të njëjtën vlerë**, dhe "
        "përmirësohen njëkohësisht edhe precizioni edhe recall-i, çka e forcon "
        "dyshimin e mësipërm për klauzolën e numrit të klasave-burim. Për Long Method "
        "fitimi është gjithashtu i "
        "qartë, por foldet ndahen mes dy vlerave dhe blihet me precizion.",
        "Për Blob dhe Data Class kalibrimi nuk ndihmon: te e para lëvizja është e "
        "vogël, te e dyta rezultati bie nën atë të pragjeve të botuara. Dhe foldet e "
        "Data Class-it nuk pajtohen as për cilin prag të lëvizin — dy prej tyre "
        "zgjedhin një prag krejt tjetër nga tre të tjerët. Kur zgjedhja varet kaq "
        "shumë nga cila pjesë e korpusit shihet, «pragu optimal» është veti e "
        "bashkësisë dhe jo e gjuhës.",
        f"Vlen të vihet re edhe dallimi me fshirjen. Ajo sugjeronte {_swept_best()} për Long "
        f"Method; kalibrimi i ndershëm jep {data['per_smell']['long method']['calibrated']['mcc']:.3f}. "
        "Diferenca është pikërisht ajo që "
        "fitohet kur zgjedhjes i lejohet ta shohë bashkësinë mbi të cilën do të "
        "raportohet, dhe arsyeja pse shifra e fshirjes nuk u adoptua.",
    ]


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
    text = f"Bashkimi e ngre recall-in mbi atë të modelit te {raised} nga {len(smells)} erërat"
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
        f"janë nën ato të modelit te {lower} nga {len(smells)} erërat."
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
    return f"foldet nuk pajtohen për të njëjtën vlerë te {split} nga {total} erërat"


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
        f"Kalibrimi jashtë-fold-it i Shtojcës 8.6, i matur veç dhe pa e parë këtë "
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
         ["Era", "Të humbura", "Shpërndarja"], spread),  # fmt: skip
        ("table", "Kur një klauzolë e vetme e ndal strategjinë",
         ["Era", "Klauzola", "Rastet", "Mediana e afrisë"], rows),  # fmt: skip
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
        f"zgjodhi për Blob-in (Nënkapitulli 5.2) ndajnë {len(shared)} nga katër vendet e "
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

    Shtojca 8.8 thotë cila klauzolë e ndali secilën mospërputhje dhe aty
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
        "Shtojca 8.8 numëron klauzolat që ndalën secilën mospërputhje, por nuk thotë si "
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
        ["Vende të detektuara", str(detected), "100%"],
        ["Të transformuara", str(applied), f"{applied / detected:.1%}"],
        ["Të refuzuara", str(data["refused"]), f"{data['refused'] / detected:.1%}"],
    ]
    if data.get("unlocatable"):
        rows.append(["Të palokalizueshme", str(data["unlocatable"]), ""])

    refusals = [
        [reason.replace("_", " "), str(count), f"{count / detected:.1%}"]
        for reason, count in sorted(data["refused_by_reason"].items(), key=lambda p: -p[1])
    ]

    verdicts = [
        [verdict.replace("_", " "), str(count), f"{count / applied:.1%}"]
        for verdict, count in sorted(data["verdicts"].items(), key=lambda p: -p[1])
    ]

    broken = data["verdicts"].get("new_errors", 0) + data["verdicts"].get("broken_syntax", 0)
    share = broken / applied if applied else 0.0

    return [
        f"Mbi {data['files']} skedarë të korpusit u detektuan {detected} vende ku motori "
        f"ka një transformim; prej tyre {applied} u transformuan.",
        ("table", "Rezultati i motorit të refaktorimit",
         ["", "Numri", "Pjesa"], rows),
        _applied_by_refactoring(data),
        "Refuzimet ndahen sipas arsyes, kuptimi i së cilës jepet te Shtojca 8.4, dhe "
        "rishkrimet e aplikuara sipas verdiktit të verifikimit.",
        ("table", "Pse u refuzuan",
         ["Arsyeja", "Numri", "Pjesa e vendeve"], refusals),
        ("table", "Verifikimi i atyre që u aplikuan",
         ["Verdikti", "Numri", "Pjesa e të aplikuarave"], verdicts),
        f"Nga {applied} rishkrime, {broken} futën një gabim që nuk ishte aty më parë "
        f"({share:.2%}). Pjesa tjetër ose kompiloi, ose nuk shtoi asnjë lloj të ri "
        "gabimi kundrejt skedarit origjinal.",
        *_resolution_paragraphs(data),
        *_project_context_paragraphs(),
        *_rewrite_quality_paragraphs(),
        *_refusal_severity_paragraphs(),
    ]


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
        f"{name} {count} ({count / applied:.1%})"
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
        f"Te {higher} nga {higher + len(reverse)} erërat, strategjia e botuar i kap "
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
        f"Precizioni i strategjive është mbi recall-in te {above} nga {len(rows)} erërat: "
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
        f"Qasja B ka MCC më të lartë se Qasja A te {len(higher)} nga {len(smells)} "
        "erërat. Pajtimi mes tyre matet me koeficientin kappa dhe me numrin e "
        "mostrave që shënon secila qasje, vetëm ose bashkë me tjetrën."
    )


def _only_rules_vs_only_model(ml: dict, smells: list) -> str:
    """Sa raste kap vetëm njëra qasje, erë për erë, nga të dhënat.

    Fjalia e mëparshme e quante «të krahasueshëm» numrin që rregulli kap vetëm te
    Feature Envy, ndërsa të dhënat japin 13 kundrejt 54 (VD-125).
    """
    parts = [
        f"{SMELL_SQ[smell]} {ml['per_smell'][smell]['vs_rules']['only_rules']} me "
        f"{ml['per_smell'][smell]['vs_rules']['only_model']}"
        for smell in smells
    ]
    widest = max(
        smells,
        key=lambda smell: ml["per_smell"][smell]["vs_rules"]["only_rules"]
        / max(ml["per_smell"][smell]["vs_rules"]["only_model"], 1),
    )
    return (
        "Numri i mostrave që shënon vetëm A, kundrejt atyre që shënon vetëm B, është: "
        + "; ".join(parts)
        + f". Raporti më i afërt mes të dyjave është te {SMELL_SQ[widest]}."
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
    return (
        f"{_opens(_rewrites(regressions))} nga {total} nuk shtonte lloj të ri gabimi i "
        "izoluar, por shton brenda projektit të vet." + _overturned_case()
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
    if len(overturned) != 1:
        return ""

    case = overturned[0]
    where = f"{case['class_name']}.{case['method']}"
    return (
        f" Rasti është një Extract Method mbi {where} te «AlertSummaryRenderer.java» "
        "e projektit Ambari, dhe të tria gabimet që shton janë paketa të palëve të "
        "treta që mungojnë në korpus."
    )


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
        [name.replace("_", " "), str(alone.get(name, 0)), str(context.get(name, 0))]
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
        _overturned(regressions, total)
        + (
            f" {unchecked} kompilime e kaluan kufirin kohor dhe numërohen si të "
            "pakontrolluara, kurrë si sukses."
            if unchecked
            else ""
        )
        + f" Matja zgjati rreth {data['seconds'] / 3600:.0f} orë.",
    ]


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
                [smell, level, str(judged), str(cell["applied"]),
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
        f"Niveli kritik ka normën më të ulët te {critical_lowest} nga {len(lowest)} "
        "erërat"
        + (
            f", dhe te {' dhe '.join(unmonotone)} niveli i mesëm ka normë më të lartë se "
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
        f"erërave veç e veç (paradoksi i Simpson-it): {high[0]} ka normë {high[1]:.1%} "
        f"dhe {high[2]:.1%} vende kritike, ndërsa {low[0]} ka {low[1]:.1%} dhe "
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
    persists = counts.get("persists", 0)

    resolved = counts.get("resolved", 0)
    return [
        "Çdo entitet i rishkruar u mat sërish, për të parë nëse detektori ende ndez "
        "mbi të.",
        ("table", "A u hoq era pas rishkrimit",
         ["Rezultati", "Numri", "Pjesa e të aplikuarave"], rows),
        f"Era u hoq në {resolved / total:.1%} të rishkrimeve dhe mbeti në "
        f"{persists / total:.1%} prej tyre.",
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
            smell,
            entry["metric_before"] and f"{entry['metric_before']:g}",
            f"{entry['metric_after']:g}",
            str(entry["sites"]),
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
    listed = ", ".join(f"{name} ({count})" for name, count in sorted(introduced.items()))
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
        name, _, source = entry["title"].partition(" (")
        strategy_rows.append(
            [
                name,
                "klasë" if entry["scope"] == "class" else "metodë",
                entry["formula"],
                source.rstrip(")") or "—",
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
            does = f"aplikohet: {entry['automated']}"
        elif entry["advisory_reason"]:
            does = "vetëm propozohet"
        else:
            does = "nuk ka transformim"
        engine_rows.append([entry["smell"], ", ".join(entry["refactorings"]), does])

    refusal_rows = [
        [reason, REFUSAL_SQ.get(reason, "[PLOTËSO: arsye e re, pa shpjegim në shtojcë]")]
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
                "dyzet e pesë sisteme Java dhe C++.",
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
                "hapat u ri-ekzekutuan mbi të njëjtat hyrje, dhe të gjithë, me një "
                "përjashtim, dhanë skedarë identikë me të komituarit, veç commit-it dhe "
                "kohëzgjatjes që regjistrojnë. Tabela e veçorive, 4.534 rreshta, doli bajt "
                "për bajt identike; po ashtu të katër modelet e stërvitura, dhe asnjë figurë "
                "nuk ndryshoi.",
                "Përjashtimi është hapi i dymbëdhjetë. Ai riprodhoi numrat që mbajnë "
                "pretendimin — po aq rishkrime, po aq verdikte «kompilon», asnjë përmbysje — "
                "por pesë kompilime që herën e parë e kaluan kufirin kohor, herën e dytë "
                "morën verdikt: ndarja mes «i kontrolluar» dhe «i pakontrolluar» varet nga "
                "ngarkesa e makinës. Ai riprodhim i përket mostrës së atëhershme prej 30 "
                "skedarësh; mostra u dyfishua më vonë, dhe dyfishimi nxori përmbysjen e "
                "vetme që raporton Kapitulli 5.",
                "Hapat 1 dhe 7 mbeten të pariekzekutuar: i pari kërkon rishkarkimin e "
                "korpusit të plotë, i dyti disa orë ekzekutimi mbi të. Për ta riprodhimi "
                "mbetet pretendim i pakontrolluar, dhe thuhet këtu si i tillë.",
            ],
        ),
    ] + secondary_results()
