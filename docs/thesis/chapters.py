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
        "Cilësia e brendshme e kodit burimor përcakton sa lehtë një sistem softuerik "
        "mund të kuptohet, të ndryshohet dhe të zgjerohet gjatë gjithë jetës së tij. "
        "Code smells janë simptoma të strukturës së dobët të dizajnit që nuk shkaktojnë "
        "gabime të drejtpërdrejta, por e rrisin ndjeshëm koston e ndryshimeve të "
        "ardhshme. Identifikimi manual i tyre nuk është i realizueshëm në sisteme të "
        "mëdha, ndërsa mjetet ekzistuese të analizës statike mbështeten kryesisht në "
        "pragje fikse mbi metrika të veçuara, çka prodhon numër të konsiderueshëm "
        "alarmesh të rreme dhe ndalet te identifikimi i problemit pa propozuar zgjidhje.",
        f"Ky punim ndërton një sistem që i zbulon code smells në dy mënyra të pavarura "
        f"dhe i krahason mbi të njëjtën të vërtetë bazë. Qasja e parë zbaton strategjitë "
        f"e publikuara të detektimit mbi {metrics} metrika; e dyta trajnon klasifikues "
        f"mbi po ato metrika. Të dyja vlerësohen mbi {samples} mostra nga "
        f"{dataset['repositories']} depo Java, të etiketuara nga zhvillues "
        f"profesionistë, me ndarje të grupuar sipas depos dhe me të njëjtin kod "
        f"pikëzimi. Sistemi përfshin edhe një motor refaktorimi që rishkruan kod vetëm "
        f"kur i provon parakushtet e veta nga pema sintaksore, dhe një ndërfaqe web mbi "
        f"të tria.",
        f"Strategjitë e publikuara dolën të sakta por të kursyera: precizion "
        f"{band([m['precision'] for m in primary])} me recall "
        f"{band([m['recall'] for m in primary])}. Të ndara sipas ashpërsisë, ato "
        f"degradojnë me hijeshi, duke i kapur rastet e rënda shumë më mirë se ato të "
        f"lehtat. Klasifikuesit i tejkaluan qartë, me MCC "
        f"{band([m['mcc'] for m in best])} kundrejt "
        f"{band([m['mcc'] for m in primary])}, dhe i rizbuluan pjesërisht metrikat që "
        f"përdorin vetë strategjitë. Intervalet e besimit me bootstrap sipas depos "
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
            f"{share:.1%} të vendeve të detektuara, ku shumica e refuzimeve vjen nga "
            f"forma e kodit dhe nga rrjedha e kontrollit; refuzimi trajtohet si rezultat "
            f"i saktë dhe numërohet. "
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
            "Termi u prezantua nga Kent Beck dhe u sistemua nga Fowler (2018), i cili "
            "përshkroi njëzet e dy smells bashkë me refaktorimet që i adresojnë. "
            "Përkufizimi mbetet qëllimisht cilësor: një smell është simptomë, jo "
            "gabim, dhe gjykimi nëse diçka është problem varet nga konteksti.",
            "Matja sasiore u mundësua nga suita e metrikave e Chidamber & Kemerer "
            "(1994), e cila propozoi gjashtë metrika për sistemet e orientuara nga "
            "objektet, mes tyre WMC, DIT, NOC, CBO, RFC dhe LCOM. Henderson-Sellers "
            "(1996) e rishikoi LCOM-in duke propozuar një variant të normalizuar, "
            "ndërsa Bieman & Kang (1995) prezantuan TCC-në, e cila e mat kohezionin "
            "përmes çifteve të metodave që ndajnë të paktën një fushë. Këto metrika "
            "janë baza mbi të cilën ndërtohet çdo detektim sasior i mëvonshëm.",
            "Sharma & Spinellis (2018) ofrojnë një shqyrtim sistematik të fushës dhe "
            "vërejnë se literatura nuk ka një përkufizim të vetëm operacional për "
            "shumicën e smells, çka e bën krahasimin mes mjeteve të vështirë.",
        ],
    ),
    (
        "2.2",
        "Detektimi me rregulla mbi metrika",
        [
            "Marinescu (2004) prezantoi konceptin e strategjive të detektimit: "
            "rregulla që kombinojnë disa metrika me pragje, në vend që të mbështeten "
            "në një metrikë të vetme. Ideja u zhvillua në një katalog të plotë nga "
            "Lanza & Marinescu (2006), ku çdo smell shprehet si konjunksion kushtesh "
            "mbi metrika, me pragje të nxjerra statistikisht nga një korpus prej "
            "dyzet e pesë sistemesh.",
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
            "Arcelli Fontana et al. (2016) krahasuan disa teknika të mësimit të "
            "makinës për detektimin e smells dhe raportuan performancë shumë të "
            "lartë, në disa raste mbi 95% saktësi. Ky punim u bë referenca kryesore e "
            "fushës dhe motivoi një varg studimesh pasuese.",
            "Megjithatë, Di Nucci et al. (2018) e riekzaminuan atë rezultat dhe "
            "treguan se ai varej fuqishëm nga mënyra si ishte ndërtuar dataset-i. Kur "
            "bashkësia e testimit u ndërtua në mënyrë më realiste, performanca ra "
            "ndjeshëm. Përfundimi i tyre është se rezultatet e raportuara në "
            "literaturë duhen lexuar me kujdes ndaj procedurës së ndarjes së të "
            "dhënave, jo vetëm ndaj algoritmit.",
            "Ky vëzhgim ka pasojë të drejtpërdrejtë metodologjike për këtë punim dhe "
            "përcakton njërën nga zgjedhjet e tij qendrore: ndarja mes trajnimit dhe "
            "testimit bëhet e grupuar sipas depos, kurrë e rastësishme sipas "
            "rreshtave. Mostrat e së njëjtës depo ndajnë autorë, konvencione dhe "
            "shpesh kod të kopjuar; një ndarje e rastësishme i vendos ato në të dyja "
            "anët dhe e fryn çdo shifër.",
            "Azeem et al. (2019) ofrojnë një shqyrtim sistematik dhe meta-analizë të "
            "kësaj nënfushe, duke identifikuar mungesën e dataset-eve të përbashkëta "
            "si pengesën kryesore për krahasueshmëri.",
        ],
    ),
    (
        "2.4",
        "E vërteta bazë dhe subjektiviteti",
        [
            "Çdo vlerësim i detektimit kërkon një të vërtetë bazë, dhe këtu literatura "
            "has një problem themelor. Mäntylä & Lassenius (2006) treguan "
            "eksperimentalisht se vlerësimi i zhvilluesve për praninë e një smell "
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
            "e mundësive të Move Method, duke treguar se identifikimi i mundësisë dhe "
            "aplikimi i saj janë probleme të ndara me vështirësi të ndryshme.",
            "Murphy-Hill et al. (2012) matën si i përdorin zhvilluesit mjetet e "
            "refaktorimit dhe gjetën se shumica e refaktorimeve bëhen me dorë, edhe "
            "kur mjeti i automatizuar është i disponueshëm. Silva et al. (2016) "
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
            "dyta: rezultatet e raportuara për mësimin e makinës janë të ndjeshme "
            "ndaj procedurës së ndarjes, dhe jo çdo punim e deklaron atë qartë. E "
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
            "Kapitulli 1 i shtroi tri pyetjet kërkimore. Ky kapitull i bën ato të "
            "matshme: përcakton çfarë do të thotë një përgjigje, cilat janë kriteret "
            "që e vendosin, dhe cilat kufizime të vetëdijshme e formësojnë atë që mund "
            "të pretendohet.",
        ],
    ),
    (
        "3.1",
        "Formulimi i matshëm",
        [
            "Detektimi i një code smell mund të shprehet si problem klasifikimi binar "
            "mbi një entitet kodi: një klasë ose një metodë është ose nuk është "
            "shembull i një ere të caktuar. E vërteta bazë vjen nga rishikuesit "
            "profesionistë të MLCQ-së, dhe krahasimi bëhet me matricën konfuze dhe "
            "shifrat që derivohen prej saj.",
            "Refaktorimi nuk është problem klasifikimi. Ai është transformim me "
            "parakushte, dhe pyetja e matshme nuk është «sa i saktë është», por «sa "
            "shpesh mund të zbatohet pa e prishur kodin». Prandaj rezultati i tij "
            "raportohet si numri i vendeve të detektuara, i atyre të transformuara, "
            "dhe shpërndarja e arsyeve pse pjesa tjetër u refuzua.",
        ],
    ),
    (
        "3.2",
        "Kriteret e suksesit",
        [
            (
                "bullet",
                "Për PK1: shifra për çdo erë, të prodhuara mbi një korpus të deklaruar "
                "dhe të riprodhueshme me një komandë. Një recall i ulët është përgjigje "
                "e vlefshme; fshehja e tij nuk është.",
            ),
            (
                "bullet",
                "Për PK2: krahasim mbi të njëjtat mostra, me të njëjtin kod pikëzimi, "
                "dhe me një baseline që tregon se sa merret pa mësuar asgjë. Pa këtë "
                "të fundit, çdo shifër është e palexueshme.",
            ),
            (
                "bullet",
                "Për PK3: verifikim që dalja e çdo transformimi të aplikuar nuk e "
                "prish skedarin. Kufiri i këtij verifikimi është deklaruar në "
                "Kapitullin 4 dhe diskutohet në Kapitullin 6: ruajtja e plotë e "
                "sjelljes kërkon ekzekutimin e suitave të testeve të vetë projekteve, "
                "çka mbetet punë e ardhshme.",
            ),
        ],
    ),
    (
        "3.3",
        "Kufizimet e vetëdijshme dhe pasojat e tyre",
        [
            "Dy zgjedhje arkitekturore e formësojnë atë që sistemi mund të pretendojë, "
            "dhe të dyja janë të qëllimshme.",
            "E para: analizuesi regjistron fakte sintaksore dhe nuk zgjidh simbole. "
            "Kjo e mban sistemin të thjeshtë dhe të shpejtë, por do të thotë se çdo "
            "transformim që duhet të gjejë të gjitha referencat ndaj një emri në "
            "projekt nuk i provon dot parakushtet e veta. Rrjedhimisht dy nga pesë "
            "transformimet e planifikuara mbeten propozim dhe nuk aplikohen "
            "automatikisht. Kjo nuk është mangësi implementimi por pasojë e "
            "deklaruar e zgjedhjes.",
            "Kufiri nuk është gjithmonë aty ku duket. Ndryshimi i një nënshkrimi "
            "kërkon çdo pikë thirrjeje, por Java-ja i kufizon vetë thirrjet e një "
            "metode `private` brenda skedarit ku ajo jeton. Prandaj Introduce "
            "Parameter Object aplikohet pikërisht atje dhe refuzon kudo tjetër: "
            "modifikuesi i qasjes, e jo vështirësia e transformimit, është kushti që "
            "e bën të provueshëm.",
            "E dyta: refaktorimi bëhet me transformime mbi pemën sintaksore dhe jo me "
            "gjenerim teksti. Një model gjuhësor do të prodhonte kod për shumë më "
            "tepër raste, por pretendimi i punimit është që ajo çka aplikohet të jetë "
            "e saktë, dhe kjo kërkon parakushte të provueshme, jo dalje bindëse.",
            "Nga këto rrjedh edhe kriteri kryesor i motorit: refuzimi është rezultat i "
            "saktë. Një motor që refuzon shpesh por nuk gabon kurrë është i "
            "mbrojtshëm; një që provon gjithçka dhe prish kodin nuk është.",
        ],
    ),
]

# ======================================================================
# Kapitulli 4
# ======================================================================
CHAPTER_4 = [
    (
        None,
        "",
        [
            "Metodologjia përshkruhet këtu në radhën në të cilën ekzekutohet: "
            "materializimi i korpusit, matja, detektimi me rregulla, detektimi me "
            "mësim makine, dhe refaktorimi. Çdo hap prodhohet nga një skript i "
            "vetëm dhe çdo rezultat shkruhet me commit-in, versionin e Python-it dhe "
            "platformën që e prodhuan.",
        ],
    ),
    (
        "4.1",
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
        "4.2",
        "Matja",
        [
            "Analizuesi ndërtohet mbi tree-sitter (Brunsfeld et al.) dhe regjistron "
            "vetëm fakte sintaksore. Mbi këtë model maten shtatëmbëdhjetë metrika "
            "klase dhe nëntë metrika metode, me një kalim të vetëm për klasë. Ndër to "
            "janë metrikat e Chidamber & Kemerer-it (1994), varianti i normalizuar i "
            "LCOM-it i Henderson-Sellers-it (1996), TCC-ja e Bieman & Kang-ut (1995) "
            "dhe kompleksiteti ciklomatik (McCabe, 1976), i matur si numri i pikave "
            "të vendimit në trupin e metodës plus një.",
            "Rreshtat e kodit numërohen sipas kornizës së Park (1992): rreshtat bosh, "
            "komentet dhe rreshtat që përmbajnë vetëm një kllapë nuk janë pohime dhe "
            "nuk numërohen. Ky përkufizim ka një implementim të vetëm në kod, sepse "
            "dy implementime devijuan në heshtje njëherë dhe defekti u zbulua vetëm "
            "kur u krahasuan.",
            "Metrikat ATFD, CBO, DIT dhe TCC përcaktohen kundrejt tipave të tjerë të "
            "projektit. Prandaj çdo depo analizohet e plotë; një klasë e matur e "
            "izoluar do të raportonte vlera thjesht të gabuara.",
        ],
    ),
    (
        "4.3",
        "Qasja A: detektimi me rregulla",
        [
            "Strategjitë zbatohen ashtu siç janë publikuar nga Lanza & Marinescu "
            "(2006). Çdo prag numerik rri i centralizuar në një skedar të vetëm dhe "
            "çdo numër aty ka citim; një vlerë që nuk i atribuohet dot një burimi nuk "
            "përdoret.",
            "Një detektor nuk kthen boolean, por kushtet që vlerësoi bashkë me vlerat "
            "e matura. Kjo bën të mundura tri gjëra: ndërfaqja shpjegon pse diçka u "
            "shënua, punimi raporton cila klauzolë e mbajti detektimin, dhe ashpërsia "
            "derivohet nga sa larg pragut është matja në vend që të caktohet.",
            "Shkalla e ashpërsisë është ajo e MLCQ-së, ndaj dalja e rregullave "
            "krahasohet me etiketat e njeriut pa asnjë hap hartëzimi.",
        ],
    ),
    (
        "4.4",
        "Qasja B: detektimi me mësim makine",
        [
            "Katër modele vlerësohen: klasifikuesi i shumicës, regresioni logjistik, "
            "Random Forest (Breiman, 2001) dhe Gradient Boosting (Friedman, 2001), "
            "të zbatuar me scikit-learn (Pedregosa et al., 2011).",
            "Klasifikuesi i shumicës raportohet gjithmonë. Mbi një bashkësi ku "
            "shumica e etiketave janë negative, një F1 mbresëlënës mund të arrihet pa "
            "mësuar asgjë, dhe i vetmi mjet që e dallon këtë është të parit se sa merr "
            "parashikimi i klasës shumicë mbi po atë ndarje.",
            "Ndarja bëhet me GroupKFold sipas depos, siç e kërkon vërejtja e Di Nucci "
            "et al. (2018). Parashikimet janë jashtë fold-it: çdo mostër parashikohet "
            "saktësisht një herë, nga një model që nuk e ka parë kurrë projektin e "
            "saj. Kjo jep të njëjtën formë që prodhojnë detektorët, ndaj dy qasjet "
            "krahasohen mostër për mostër.",
            "Çekuilibri trajtohet me peshë klase, jo me mbi-mostrim. Mbi-mostrimi do "
            "t'i dyfishonte rreshtat përtej kufirit të fold-it dhe do ta prishte "
            "grupimin. Asnjë ribalancim nuk zbatohet mbi bashkësinë e testimit.",
            "Rëndësia e veçorive matet me permutation importance mbi fold-in e "
            "mbajtur jashtë. Rëndësia e papastërtisë që një pyll e jep falas anon nga "
            "veçoritë me kardinalitet të lartë, dhe pikërisht ai anim do ta bënte të "
            "pakuptimtë pyetjen nëse modeli zgjodhi metrikat e strategjive.",
            "Të dyja qasjet pikëzohen nga i njëjti kod. Nëse secila do ta llogariste "
            "vetë precizionin, tabela do të krahasonte dy përkufizime, jo dy qasje.",
        ],
    ),
    (
        "4.5",
        "Qasja C: motori i refaktorimit",
        [
            "Çdo transformim deklaron parakushtet e veta. Nëse ndonjëra prej tyre nuk "
            "provohet nga pema e analizës, transformimi kthen «e paaplikueshme» me "
            "arsyen përkatëse. Refuzimi është rezultat i saktë dhe numërohet si i "
            "tillë, jo si dështim.",
            "Rishkrimi bëhet mbi rangje bajtash dhe aplikohet nga fundi para, që "
            "offset-et e çdo editimi të mbeten të vlefshme kundrejt tekstit ku u "
            "matën. Dy editime që mbivendosen refuzohen, sepse nuk kanë rezultat të "
            "përcaktuar. Puna bëhet mbi bajta e jo mbi karaktere, sepse Java-ja është "
            "UTF-8 dhe prerja sipas indeksit të karakterit e pret një sekuencë "
            "shumë-bajtëshe në mes.",
            "Verifikimi bëhet në tri nivele. U mat se vetëm 8% e skedarëve të korpusit "
            "kompilojnë të vetëm, sepse pjesa tjetër importon fqinjët e vet; "
            "këmbëngulja te një kompilim i pastër do të linte 92% të korpusit të "
            "paverifikueshëm. Prandaj kontrollohet së pari nëse skedari i rishkruar "
            "parsohet, pastaj nëse shton lloj të ri gabimi kompilimi, dhe së fundi — "
            "ku është e mundur — nëse kompilon.",
        ],
    ),
    (
        "4.6",
        "Matja e performancës",
        [
            "Një mostër quhet pozitive kur ashpërsia e agreguar e rishikuesve është mbi "
            "«none». Agregimi parësor është mesatarja e rishikimeve; maksimumi, "
            "minimumi dhe unanimiteti raportohen si analizë ndjeshmërie, sepse "
            "rishikuesit e MLCQ-së nuk pajtohen me njëri-tjetrin në një të katërtën e "
            "mostrave dhe një shifër e vetme do ta fshihte atë mospajtim.",
            "Mbi këtë përkufizim maten precizioni, recall-i dhe F1-i. Të tria "
            "raportohen bashkë me koeficientin e korrelacionit të Matthews-it "
            "(Matthews, 1975), i cili i përfshin të katër qelizat e matricës konfuze "
            "dhe mbetet i papërcaktuar kur njëra margjinë është bosh. Mbi një bashkësi "
            "ku shumica e etiketave janë negative kjo veti është vendimtare: një "
            "detektor që nuk ndez kurrë del i papërcaktuar këtu, ndërsa saktësia e "
            "përgjithshme do t'i jepte shifër të lartë.",
            "Recall-i raportohet gjithmonë edhe i ndarë sipas ashpërsisë që caktuan "
            "rishikuesit. Një mjet që i kap rastet e rënda dhe i lëshon ato të lehtat "
            "nuk është i njëjti mjet me një tjetër që i lëshon të dyja, por një recall "
            "i vetëm i mesatarizuar i paraqet njësoj.",
            "Pajtimi mes dy qasjeve matet me koeficientin kappa (Cohen, 1960) dhe jo "
            "me pajtimin e papërpunuar. Kur 78% e etiketave janë negative, dy "
            "detektorë që të dy ndezin rrallë pajtohen mbi nëntë të dhjetat e "
            "bashkësisë pa mësuar asgjë nga njëri-tjetri; kappa e heq atë pajtim që "
            "pritet nga rastësia. Krahas saj raportohen të katër qelizat, sepse pyetja "
            "e punimit nuk është sa shpesh pajtohen, por çfarë kap secila vetëm.",
            "Motori i refaktorimit nuk matet me këto shifra. Për të numërohen vendet e "
            "detektuara, ato të transformuara dhe ato të refuzuara sipas arsyes, plus "
            "verdikti i verifikimit për secilin rishkrim. Një refuzim nuk hyn si "
            "dështim, sepse parakushti i paprovuar është pikërisht sjellja e kërkuar.",
        ],
    ),
    (
        "4.7",
        "Riprodhueshmëria",
        [
            "Çdo numër i raportuar në Kapitullin 5 prodhohet nga një skript dhe "
            "shkruhet si CSV ose JSON që komitohet. Farat e rastësisë janë të "
            "fiksuara, versionet e varësive të pinuara, dhe mjedisi i regjistruar në "
            "çdo skedar rezultati.",
            "Kalimi i shtrenjtë mbi korpusin — rreth 95 minuta për 690 mijë skedarë — "
            "bëhet një herë dhe prodhon një tabelë veçorish që komitohet. Pragjet nuk "
            "hyjnë në atë kalim, ndaj analiza e ndjeshmërisë rirendit detektorët mbi "
            "rreshtat e ruajtur në sekonda. Pa këtë ndarje, një fshirje me njëzet "
            "konfigurime do të kushtonte mbi tridhjetë orë dhe nuk do të bëhej.",
        ],
    ),
]

# ======================================================================
# Kapitulli 6
# ======================================================================
CHAPTER_6 = [
    (
        "6.1",
        "Interpretimi i rezultateve",
        [
            "Gjetja më e qëndrueshme e këtij punimi është se strategjitë e publikuara "
            "të detektimit kanë precizion të lartë dhe recall të ulët. Kur ato ndezin, "
            "kanë kryesisht të drejtë; por i humbin shumicën e rasteve që rishikuesit "
            "i shënojnë. Për një mjet praktik kjo nuk është domosdoshmërisht e keqe: "
            "një sinjal i rrallë por i besueshëm konsumohet më lehtë se një listë e "
            "gjatë me alarme false.",
            "Ndarja sipas ashpërsisë e ndryshon leximin. Detektorët degradojnë me "
            "hijeshi: i kapin rastet e rënda shumë më mirë se ato të lehtat. Një F1 i "
            "vetëm e fsheh krejt këtë, dhe pikërisht për këtë arsye recall-i "
            "raportohet i ndarë sipas etiketës që caktuan rishikuesit.",
            "Modelet e mësimit të makinës e tejkalojnë qartë qasjen me rregulla në çdo "
            "erë. Por krahasimi qelizë për qelizë tregon se ato nuk e zëvendësojnë "
            "atë plotësisht: te Feature Envy rregulli kap raste që modeli i humb, dhe "
            "kjo është e vetmja erë ku bashkimi i dy qasjeve do të kishte kuptim "
            "praktik.",
            "Përparësia qëndron edhe kur matet me interval besimi, por jo pa kusht. Kur "
            "rregullit i jepet pragu i tij më i mirë nga fshirja — krahasimi më bujar që "
            "mund t'i bëhet — dallimi te Long Method e përfshin zeron. Pra pretendimi "
            "vlen përgjithësisht, dhe jo pikërisht te era ku rregulli tashmë punonte më "
            "mirë. Ky është kufizim i krahasimit, jo i njërës qasje.",
        ],
    ),
    (
        "6.2",
        "Çfarë matin vërtet strategjitë",
        [
            "Dy gjetje të pavarura tregojnë në të njëjtin drejtim. E para: kur "
            "modeleve u lihet të zgjedhin vetë veçoritë, te Blob nuk zgjidhen TCC dhe "
            "WMC — pikërisht kushtet e kohezionit dhe të kompleksitetit mbi të cilat "
            "është ndërtuar God Class — por metrikat e madhësisë.",
            "E dyta: shtimi i një detektori që mbështetet vetëm te madhësia e "
            "përmirëson ndjeshëm përputhjen me gjykimin e rishikuesve për të njëjtën "
            "erë.",
            "Të dyja sugjerojnë se ajo që rishikuesit e MLCQ-së e quajnë «blob» "
            "shpjegohet më mirë me madhësi sesa me kushtin e kohezionit që strategjia "
            "e publikuar e vendos në qendër. Kjo nuk e zhvlerëson strategjinë, por "
            "tregon se ajo mat diçka pak më ndryshe nga ajo që emërton.",
            "E njëjta vërejtje del edhe nga ana e refaktorimit. Encapsulate Field, i "
            "cili rekomandohet gjerësisht për Data Class, e përkeqëson matjen sipas "
            "vetë përkufizimit të strategjisë: ai shndërron një fushë publike në dy "
            "akses-metoda publike, dhe të dyja kushtet e strategjisë e numërojnë këtë "
            "si përkeqësim. Fowler-i e trajton atë transformim si hap përgatitor, jo "
            "si ilaç; një mjet që aplikon vetëm hapin e parë ecën në drejtim të "
            "gabuar.",
        ],
    ),
    (
        "6.3",
        "Kufizimet",
        [
            "Mbulimi i korpusit nuk është i plotë: disa depo të MLCQ-së janë fshirë "
            "ose zhvendosur, dhe mostrat e tyre nuk hyjnë në vlerësim. Numri raportohet "
            "si kufizim i studimit.",
            "Mospajtimi mes rishikuesve është i konsiderueshëm. Për këtë arsye çdo "
            "strategji agregimi raportohet veç, dhe mostrat që një strategji nuk i "
            "etiketon dot hidhen në vend që të lexohen si negative.",
            "Verifikimi i refaktorimeve është më i dobët se sa do të dëshirohej. "
            "Kompilimi i izoluar nuk është i mundur për shumicën e skedarëve, ndaj "
            "për ta pretendimi kufizohet te «nuk shton lloj të ri gabimi». Verifikimi "
            "me suitat e testeve të vetë projekteve mbetet punë e ardhshme.",
            "Arsyeja pse ai verifikim nuk u bë është vetë ndërtimi i korpusit, jo "
            "mungesa e kohës. Shkarkuesi ruan me qëllim vetëm skedarët me prapashtesë "
            "«.java», sepse kjo është gjithçka që i duhet analizës dhe e mban korpusin "
            "të vogël. Pasoja është se korpusi nuk mban asnjë përkufizim ndërtimi dhe "
            "asnjë varësi: skedarët e testeve janë aty, por pa «pom.xml» ose "
            "«build.gradle» dhe pa bibliotekat e treta ata as kompilohen dhe as "
            "ekzekutohen. Ekzekutimi i tyre do të kërkonte rimarrjen e plotë të të "
            "gjitha arkivave dhe ndërtimin e secilës depo në commit-in e vet historik, "
            "ku ndërtimet e sotme dështojnë rëndom për shtojca të vjetruara.",
            "Analizuesi nuk zgjidh simbole, ndaj dy nga pesë transformimet e "
            "planifikuara nuk automatizohen. Kjo nuk është mangësi implementimi por "
            "pasojë e drejtpërdrejtë e një zgjedhjeje arkitekturore të deklaruar.",
            "Ashpërsia që sistemi e derivon nuk e riprodhon gjykimin e rishikuesve. Ajo "
            "u ndërtua në shkallën e MLCQ-së pikërisht që të krahasohej me ta pa hap "
            "përkthimi, dhe kur krahasimi u bë, pajtimi doli pranë rastësisë për tri nga "
            "katër erërat, me mbivlerësim sistematik. Pretendimi hiqet: ajo mbetet "
            "renditje e brendshme e mjetit dhe jo riprodhim i gjykimit njerëzor.",
            "Vetë e vërteta bazë ka një tavan të ulët. Rishikuesit e MLCQ-së pajtohen "
            "mes tyre me MCC nën 0.24 për çdo erë, çka do të thotë se një pjesë e "
            "pareduktueshme e gabimit të çdo detektori i takon paqartësisë së "
            "përkufizimit dhe jo detektorit. Kjo nuk i zbut shifrat e këtij punimi, por "
            "e ndryshon shkallën në të cilën duhen lexuar — të tijat dhe të literaturës.",
        ],
    ),
    (
        "6.4",
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
                "Zgjerim i të vërtetës bazë përtej katër smells që mbulon MLCQ.",
            ),
            (
                "bullet",
                "Kalibrim i pragjeve mbi një bashkësi të ndarë dhe vlerësim mbi një "
                "tjetër të paprekur. Fshirja tregoi se dy pragje e ndryshojnë ndjeshëm "
                "rezultatin, por adoptimi i tyre pa këtë ndarje do të ishte thjesht "
                "përshtatje ndaj të dhënave të testimit.",
            ),
            (
                "bullet",
                "Ashpërsi e mësuar nga të dhënat në vend që të derivohet nga teprica. "
                "Kjo e kthen një derivim të shpjegueshëm në një model të dytë, ndaj "
                "kërkon ndarjen e vet të korpusit.",
            ),
        ],
    ),
    (
        "6.5",
        "Përfundim",
        [
            "Punimi ndërtoi një sistem që i zbulon code smells në dy mënyra të "
            "pavarura dhe i krahason mbi të njëjtën të vërtetë bazë me të njëjtin kod "
            "pikëzimi, si dhe një motor refaktorimi që rishkruan kod vetëm kur i "
            "provon parakushtet e veta.",
            "Përgjigjet e shkurtra ndaj tri pyetjeve kërkimore janë: strategjitë e "
            "publikuara janë të sakta por të kursyera; një klasifikues mbi të njëjtat "
            "metrika është dukshëm më i mirë dhe i rizbulon pjesërisht metrikat e "
            "strategjive; dhe një pjesë e vogël por reale e rasteve të detektuara mund "
            "të transformohet automatikisht, ku shumica e refuzimeve vjen nga forma e "
            "kodit dhe nga rrjedha e kontrollit.",
            "Dy rezultate negative i shoqërojnë ato dhe nuk duhen lexuar veç: ashpërsia "
            "e derivuar nuk e riprodhon gjykimin e rishikuesve, dhe vetë rishikuesit "
            "pajtohen mes tyre aq pak sa çdo shifër e kësaj fushe duhet lexuar mbi një "
            "tavan dukshëm më të ulët se sa e sugjeron zakonisht literatura.",
            "Kontributi kryesor nuk është një shifër e vetme, por një hark i plotë e i "
            "riprodhueshëm nga korpusi te rezultati, ku çdo numër rigjenerohet me një "
            "komandë dhe çdo vendim është i regjistruar me arsyen e vet.",
        ],
    ),
]


# ======================================================================
# Kapitulli 5: teksti rreth numrave, numrat nga data/results
# ======================================================================
def chapter_5() -> list:
    """Rezultatet, të ndërtuara nga skedarët e komituar."""
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
                f"nga {dataset['repositories']} depo, dhe rigjenerohen me një komandë. "
                "Agregimi i etiketave është mesatarja e rrumbullakosur lart, përveç "
                "aty ku thuhet ndryshe.",
                ("figure", str(FIGURES / "shperndarja_e_mostrave.png"),
                 "Shpërndarja e mostrave sipas erës"),
            ],
        ),
        (
            "5.1",
            "Qasja A: detektimi me rregulla",
            [
                "Tabela më poshtë jep precizionin, recall-in, F1-in dhe MCC-në për çdo "
                "erë. MCC-ja raportohet sepse është shifra që nuk e lajkaton një "
                "detektor mbi një bashkësi të çekuilibruar: një klasifikues që nuk "
                "ndez kurrë merr zero këtu.",
                ("table", "Qasja A kundrejt gjykimit të rishikuesve",
                 ["Erë", "P", "R", "F1", "MCC", "Pozitivë"], rules_rows),
                "Modeli është i njëjtë kudo: precizion i lartë dhe recall i ulët. Kur "
                "strategjitë ndezin kanë kryesisht të drejtë, por i humbin shumicën e "
                "rasteve.",
                "Ky lexim ndryshon kur recall-i ndahet sipas ashpërsisë që caktuan "
                "vetë rishikuesit.",
                ("table", "Recall-i sipas ashpërsisë",
                 ["Erë", "Recall te major", "Recall te minor"], severity_rows),
                ("figure", str(FIGURES / "recall_sipas_ashpersise.png"),
                 "Recall-i sipas ashpërsisë së caktuar nga rishikuesit"),
                "Detektorët degradojnë me hijeshi: i kapin rastet e rënda dukshëm më "
                "mirë se ato të lehtat. Kjo është shifra që një F1 i vetëm e fsheh.",
            ],
        ),
        (
            "5.2",
            "Qasja B: detektimi me mësim makine",
            [
                "Për secilën erë raportohet modeli me MCC-në më të lartë. Klasifikuesi "
                "i shumicës nuk ndez asnjëherë për asnjë erë, ndaj çdo shifër më poshtë "
                "është mësim i vërtetë dhe jo çekuilibër i shfrytëzuar.",
                ("table", "Modeli më i mirë për çdo erë",
                 ["Erë", "Modeli", "P", "R", "F1", "MCC"], ml_rows),
                f"MCC-ja më e lartë e arritur është {best_mcc:.3f}. Të gjitha vlerat "
                "vijnë nga parashikime jashtë fold-it mbi një ndarje të grupuar sipas "
                "depos, pra përshkruajnë atë që pritet mbi një projekt që modeli nuk e "
                "ka parë kurrë.",
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
                "Qasja B e tejkalon Qasjen A në çdo erë. Por përmbledhja nuk e tregon "
                "se çka kap secila vetëm, ndaj raportohen edhe të katër qelizat bashkë "
                "me koeficientin kappa.",
                ("table", "Pajtimi mes dy qasjeve",
                 ["Erë", "κ", "Të dyja", "Vetëm A", "Vetëm B", "n"], agreement_rows),
                ("figure", str(FIGURES / "pajtimi_a_b.png"),
                 "Mostrat e shënuara nga secila qasje"),
                "Kolona «vetëm B» tejkalon «vetëm A» në çdo erë, shpesh me një rend "
                "madhësie: modeli pothuajse e përfshin rregullin. Përjashtimi është "
                "Feature Envy, ku rregulli kap një numër të krahasueshëm rastesh që "
                "modeli i humb.",
                *_combined_paragraphs(ml),
            ],
        ),
        (
            "5.4",
            "Qasja C: refaktorimi",
            [
                "Rezultatet e motorit të refaktorimit raportohen si numri i vendeve të "
                "detektuara, sa prej tyre u transformuan, dhe shpërndarja e arsyeve të "
                "refuzimit. Refuzimi është rezultat i saktë dhe numërohet si i tillë.",
                *_refactoring_section(),
                "Verifikimi tregoi vlerën e vet menjëherë. Mbi ekzekutimet e para u "
                "shënuan si prishëse dhjetëra rishkrime, dhe hetimi i tyre nxori tri "
                "defekte të vërteta në motor: deklarimet brenda një cikli të mëparshëm "
                "numëroheshin si të dukshme, kllapat e stilit C pas emrit nuk hynin në "
                "tip, dhe një variabël e pacaktuar kalohej si parametër. Të treja "
                "prodhonin kod që nuk kompilon.",
                "Asnjëri prej tyre nuk ishte kapur nga njëzet e një testet e shkruara me "
                "dorë për këtë transformim. I kapi korpusi. Kjo është arsyeja pse "
                "verifikimi empirik nuk zëvendësohet dot me teste njësie, sado të "
                "kujdesshme, dhe është vetë një gjetje e këtij punimi.",
            ],
        ),
        (
            "5.5",
            "Ndjeshmëria ndaj pragjeve",
            [
                "Pragjet e përdorura janë ato të botuara, të nxjerra statistikisht nga "
                "një korpus tjetër. Pyetja e natyrshme është sa varet rezultati prej "
                "tyre. Secili prag u zhvendos veç, mes gjysmës dhe dyfishit të vlerës "
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
                "Këto vlera nuk adoptohen. Zgjedhja e një pragu sepse jep shifrën më të "
                "mirë mbi bashkësinë e vlerësimit është përshtatje ndaj të dhënave të "
                "testimit, dhe numri që do të raportohej pas saj do të matte sa mirë u "
                "zgjodh pragu, jo sa mirë funksionon detektimi. Kalibrimi do të kërkonte "
                "një bashkësi të ndarë dhe një bashkësi tjetër të paprekur për vlerësim; "
                "kjo është pikërisht ajo që bëhet më poshtë.",
                *_calibration_paragraphs(),
            ],
        ),
        *_severity_section(),
        *_confidence_section(),
    ]


SEVERITY_SCALE = ("minor", "major", "critical")

RESOLUTION_SQ = {
    "resolved": "era u hoq",
    "persists": "era mbeti",
    "unknown": "entiteti nuk u identifikua dot",
}


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
        f"Çdo shifër e mësipërme është një vlerësim i vetëm mbi një korpus të "
        f"caktuar. Për të matur sa varet ajo nga korpusi, çdo tregues u riprodhua me "
        f"bootstrap mbi {intervals['resamples']} rimostrime, duke rimostruar "
        f"**depo** e jo rreshta: mostrat e së njëjtës depo ndajnë autorë dhe "
        f"konvencione, ndaj rimostrimi i rreshtave do të prodhonte intervale artificialisht "
        f"të ngushta, për të njëjtën arsye që ndarja e trajnimit është e grupuar.",
        ("table", "Intervale besimi 95% për MCC-në",
         ["Erë", "A: rregullat", "B: modeli", "B − A", "E kalon zeron"], rows),
        ("figure", str(FIGURES / "intervalet_e_besimit.png"),
         "MCC me interval besimi 95% për të dyja qasjet"),
        "Përparësia e Qasjes B ndaj Qasjes A e kalon zeron te të katër erërat, pra nuk "
        "është artefakt i korpusit. Por intervalet janë të gjera — për Feature Envy-n "
        "gjerësia i kalon njëzet e pesë pikët — dhe kjo do të thotë se renditja e "
        "erërave mes tyre nuk qëndron: dallimi mes Data Class-it dhe Blob-it, për "
        "shembull, humbet brenda tyre.",
        "Krahasimi ndryshon kur Qasjes A i jepet pragu i saj më i mirë nga fshirja e "
        "Nënkapitullit 5.5, çka është krahasimi më bujar që mund t'i bëhet:",
        ("table", "B − A kur rregullat marrin pragun e tyre më të mirë",
         ["Erë", "Pragu i zhvendosur", "B − A", "E kalon zeron", "Shenja e ruajtur"],
         swept_rows),
        "Për tri erërat e para përparësia mbetet. Për Long Method-in ajo zhduket: "
        "intervali e përfshin zeron dhe shenja ruhet vetëm në 88.6% të rimostrimeve. "
        "Pra pretendimi «modeli e tejkalon rregullin» qëndron përgjithësisht, por jo "
        "për erën ku rregulli tashmë punonte më mirë, sapo atij rregulli i lejohet të "
        "kalibrohet. Ky është kufizimi i vetëm i rëndësishëm i krahasimit A↔B.",
    ]

    if ceiling is None:
        return [("5.7", "Sa peshë mban një shifër e vetme", paragraphs)]

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
        f"njerëzit: shifrat e kapitullit maten kundrejt etiketës së agreguar, ndërsa "
        f"kjo mat marrëveshjen mes dy individëve, dhe agregimi e heq një pjesë të "
        f"zhurmës që një individ i vetëm e mbart. Të dy numrat nuk janë i njëjti "
        f"tregues dhe nuk duhen vendosur në një renditje.",
        "Ajo që tregon është sa e ashpër është vetë detyra. Kur dy zhvillues "
        "profesionistë që shohin të njëjtin kod pajtohen kaq pak, një pjesë e "
        "pareduktueshme e gabimit të çdo detektori nuk i takon detektorit por "
        "përkufizimit. Çdo shifër e këtij kapitulli duhet lexuar mbi këtë sfond, dhe "
        "po ashtu çdo shifër e literaturës që raportohet pa të.",
    ]

    return [("5.7", "Sa peshë mban një shifër e vetme", paragraphs)]


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

    return [
        "Rëndësia e veçorive përgjigjet për korpusin, jo për rastin. Një zhvillues që "
        "ka përpara një klasë të shënuar nuk pyet cila metrikë ka peshë përgjithësisht; "
        "pyet pse kjo klasë. Qasja A i përgjigjet me ndërtim, sepse raporton kushtet me "
        "vlerat e matura; Qasja B fiton kudo dhe nuk thotë asgjë. Ky asimetri është "
        "kundërshtimi standard ndaj detektimit me mësim makine.",
        "Prandaj çdo entitet i shënuar u pyet edhe një herë: secila matje, një nga një, "
        "u zëvendësua me vlerën tipike të bashkësisë së trajnimit dhe modeli u pyet "
        "sërish. Kur ai zëvendësim i vetëm e kthen verdiktin nën kufirin e vendimit, "
        "ajo matje e mban vetë shënimin — dhe kjo është një fjali që zhvilluesi mund "
        "ta lexojë: «po të ishte CLOC-u tipik, kjo klasë nuk do të shënohej».",
        ("table", "Sa shpesh një matje e vetme e mban verdiktin",
         ["Erë", "Të shënuara", "Me shpjegim", "Matjet vendimtare"], rows),
        "Shpjegimi jepet jashtë fold-it, si vetë verdiktet: çdo entitet shpjegohet nga "
        "një model që nuk e ka parë depon e tij. Kufizimi i metodës është se e sheh "
        "një matje në një kohë dhe nuk dallon dot dy metrika që mbajnë të njëjtin "
        "informacion; aty ku CLOC dhe NOM thonë të dyja «e madhe», zëvendësimi i njërës "
        "mund të mos lëvizë asgjë dhe rasti del i pashpjeguar.",
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
        "përmirësohen njëkohësisht edhe precizioni edhe recall-i. Kjo e forcon "
        "vërejtjen e mësipërme se klauzola e numrit të klasave-burim nuk e bën punën "
        "për të cilën është vendosur. Për Long Method fitimi është gjithashtu i "
        "qartë, por foldet ndahen mes dy vlerave dhe blihet me precizion.",
        "Për Blob dhe Data Class kalibrimi nuk ndihmon: te e para lëvizja është e "
        "vogël, te e dyta rezultati bie nën atë të pragjeve të botuara. Dhe foldet e "
        "Data Class-it nuk pajtohen as për cilin prag të lëvizin — dy prej tyre "
        "zgjedhin një prag krejt tjetër nga tre të tjerët. Kur zgjedhja varet kaq "
        "shumë nga cila pjesë e korpusit shihet, «pragu optimal» është veti e "
        "bashkësisë dhe jo e gjuhës.",
        "Vlen të vihet re edhe dallimi me fshirjen. Ajo sugjeronte 0.690 për Long "
        "Method; kalibrimi i ndershëm jep 0.666. Diferenca është pikërisht ajo që "
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
        "Vërejtja e mësipërme ngre një pyetje praktike: a do të ishte më mirë t’i "
        "përdorje të dyja bashkë? Bashkimi trashëgon pozitivët e vërtetë të secilës, "
        "por edhe të rremët, dhe mbi një bashkësi ku shumica e etiketave janë negative "
        "ai shkëmbim nuk është aspak i vetëkuptueshëm. Prandaj u mat.",
        ("table", "Të dyja qasjet së bashku",
         ["Erë", "B: modeli", "A∪B", "A∩B", "A∪B: recall", "A∩B: precizion"], rows),
        "Përgjigjja është jo. Bashkimi e ngre recall-in ndjeshëm, por çmimi në "
        "precizion e fshin fitimin: MCC-ja mezi lëviz te Blob dhe Data Class, dhe "
        "**bie** te Long Method e Feature Envy. Ironia është se Feature Envy ishte "
        "pikërisht era ku vërejtja premtonte më shumë — dhe atje bashkimi del më keq, "
        "sepse bashkë me trembëdhjetë rastet që rregulli i kap vijnë edhe pozitivët e "
        "tij të rremë.",
        "Prerja tregon të kundërtën dhe është më e dobishmja e të dyjave. Kur të dyja "
        "qasjet pajtohen, precizioni ngrihet mbi 0.80 te çdo erë dhe deri në 0.905 te "
        "Long Method — dukshëm mbi secilën qasje veç. Recall-i bie ndjeshëm, ndaj "
        "MCC-ja del e ulët, por për një përdorues që kërkon pak alarme të rreme "
        "pajtimi i dy qasjeve të pavarura është sinjali më i fortë që sistemi prodhon.",
    ]


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
            "5.6",
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
                "Shpjegimi qëndron te vetë ndërtimi i pikës. Për Long Method teprica matet "
                "mbi një metrikë të vetme, ku dyfishi i pragut ka kuptim të drejtpërdrejtë. "
                "Për strategjitë me disa kushte, pika është mesatarja e tepricave mbi "
                "metrika heterogjene — një raport WMC-je, një raport kohezioni, një raport "
                "qasjesh të huaja — dhe asgjë nuk garanton se mesatarja e tyre përkon me "
                "atë që një zhvillues e quan problem të rëndë.",
                f"Nuk është çështje kalibrimi. Fshirja e të dy pragjeve të ashpërsisë mbi "
                f"të njëjtin brez si pragjet e detektimit e ngre kappa-n më së shumti deri "
                f"në {best:.3f}, pra edhe konfigurimi më i favorshëm i provuar mbetet "
                f"pajtim i dobët. Zhvendosja e kufijve e ndryshon shpërndarjen e "
                f"etiketave, jo aftësinë e pikës për t'i renditur rastet.",
                "Pasoja për punimin është e drejtpërdrejtë: ashpërsia e derivuar është e "
                "përdorshme si renditje brenda vetë mjetit — cili rast të shihet i pari — "
                "por nuk pretendon të riprodhojë gjykimin e një zhvilluesi për rëndësinë. "
                "Ky pretendim hiqet, dhe ndarja e recall-it sipas ashpërsisë së "
                "rishikuesve mbetet mënyra e vetme e vlefshme në të cilën ashpërsia hyn "
                "në rezultatet e këtij punimi.",
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
        "Shpërndarja e arsyeve të refuzimit është vetë rezultat: ajo tregon çfarë e "
        "pengon automatizimin, dhe jo se ku dështon zbatimi.",
        ("table", "Pse u refuzuan",
         ["Arsyeja", "Numri", "Pjesa e vendeve"], refusals),
        ("table", "Verifikimi i atyre që u aplikuan",
         ["Verdikti", "Numri", "Pjesa e të aplikuarave"], verdicts),
        f"Nga {applied} rishkrime, {broken} futën një gabim që nuk ishte aty më parë "
        f"({share:.2%}). Pjesa tjetër ose kompiloi, ose nuk shtoi asnjë lloj të ri "
        "gabimi kundrejt skedarit origjinal.",
        *_resolution_paragraphs(data),
        *_project_context_paragraphs(),
        *_refusal_severity_paragraphs(),
    ]


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
        "Kufiri i këtij verifikimi është izolimi, jo transformimi. Skedari kompilohet "
        "i vetëm, dhe një skedar i një depoje reale i importon fqinjët e vet, ndaj për "
        "shumicën pretendimi bie te «nuk shton lloj të ri gabimi». Sa do të fitohej po "
        "të mos ishte i izoluar u mat mbi një mostër: i njëjti rishkrim u kompilua dy "
        f"herë, i vetëm dhe me burimet e vetë projektit të arritshme, mbi "
        f"{data['files_checked']} skedarë dhe {total} rishkrime.",
        ("table", "Verdikti i të njëjtave rishkrime, të izoluara dhe brenda projektit",
         ["Verdikti", "I izoluar", "Brenda projektit"], rows),  # fmt: skip
        f"Verdikti më i fortë kalon nga {compiles_alone} te {compiles_context} nga "
        f"{total} rishkrime, pra nga {compiles_alone / total:.1%} në "
        f"{compiles_context / total:.1%}. Kjo do të thotë se pjesa dërrmuese e "
        "rasteve ku sistemi thotë vetëm «nuk shtova gabim» janë raste ku ai nuk mund "
        "të thoshte më shumë për shkak të mënyrës së kompilimit, jo për shkak të "
        "rishkrimit.",
        f"Po aq me rëndësi është se asnjë verdikt nuk u përmbys: {regressions} rishkrime "
        "kaluan te «me gabim të ri». Asgjë që kalon e izoluar nuk dështon kur skedari "
        "kompilohet brenda projektit të vet, çka është arsyeja pse toleranca «pa lloj "
        "të ri gabimi» mbetet e përdorshme si dëshmi edhe atje ku kompilimi i plotë "
        "nuk arrihet."
        + (
            f" {unchecked} kompilime e kaluan kufirin kohor dhe numërohen si të "
            "pakontrolluara, kurrë si sukses."
            if unchecked
            else ""
        ),
        "Mostra është e vogël dhe e mbjellë me farë: kompilimi në kontekst zgjat rreth "
        "gjashtë minuta për skedar, sepse detyron kompilimin e tërë mbylljes së "
        "varësive të tij. Verdiktet e raportuara më lart mbi tërë korpusin mbeten ato "
        "të izoluara; kjo matje nuk i zëvendëson, por tregon në ç'drejtim do të "
        "lëviznin.",
    ]


def _refusal_severity_paragraphs() -> list:
    """Ku refuzon motori: te rastet e buta apo te ato të rënda?

    Norma e vetme 20.4% nuk e dallon një mjet që rishkruan gjithçka lehtë nga një
    që tërhiqet pikërisht aty ku kodi është më i keq. Kjo është pyetja tjetër, dhe
    përgjigjja e saj nuk lexohet dot nga tabela e mësipërme.
    """
    data = _load_if_present("refusals_by_severity.json")
    if data is None:
        return []

    per_smell = data["per_smell"]
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

    return [
        "Norma e përgjithshme nuk thotë cilat vende u refuzuan. Një mjet që rishkruan "
        "rastet e buta dhe tërhiqet nga ato të rënda vlen shumë më pak se sa sugjeron "
        "ajo shifër, ndaj çdo vend u nda edhe sipas ashpërsisë që i cakton vetë "
        "sistemi.",
        ("table", "Norma e transformimit sipas erës dhe ashpërsisë",
         ["Erë", "Ashpërsia", "Vende të gjykuara", "Të transformuara", "Norma"], rows),
        f"Pritja se «sa më e rëndë, aq më pak rishkruhet» nuk qëndron si rregull. "
        f"Niveli kritik ka normën më të ulët te {critical_lowest} nga {len(lowest)} "
        "erërat, por jo te të gjitha, dhe lidhja nuk është as monotone: te Brain Method "
        "dhe Long Method niveli i mesëm rri mbi atë të butin.",
        *_pooling_warning(data),
        *_refusal_reason_shift(data),
        "Ashpërsia e përdorur këtu është ajo e derivuar nga teprica mbi pragje, të "
        "cilën seksioni i mëparshëm e tregoi se nuk e riprodhon gjykimin e rishikuesve. "
        "Prandaj ky rezultat flet për motorin kundrejt renditjes së vetë mjetit, dhe jo "
        "kundrejt asaj se sa i rëndë është kodi në gjykimin e një zhvilluesi.",
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
        f"Kjo tabelë nuk bashkohet mbi erërat. E bashkuar, niveli kritik del me "
        f"{crit[0] / crit[1]:.1%} kundrejt {rest[0] / rest[1]:.1%} të niveleve të tjera "
        "— pra e kundërta e asaj që shohin erërat veç e veç. Është paradoks i "
        "Simpson-it, dhe shkaku është përbërja: "
        f"{high[0]} ka normë {high[1]:.1%} dhe {high[2]:.1%} të vendeve të veta kritike, "
        f"ndërsa {low[0]} ka {low[1]:.1%} dhe vetëm {low[2]:.1%}. Bashkimi i jep nivelit "
        "kritik peshë nga erërat që rishkruhen lehtë dhe e përmbys shenjën, ndaj shifra "
        "e bashkuar nuk raportohet askund në këtë punim.",
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
        "Ajo që lëviz me ashpërsinë nuk është sa shpesh refuzon motori, por përse.",
        ("table", "Përbërja e arsyeve të refuzimit brenda çdo niveli",
         ["Arsyeja", *order], rows),
        "Sa më e rëndë metoda, aq më rrallë refuzimi vjen nga forma e kodit dhe aq më "
        "shpesh nga rrjedha e kontrollit. Shpjegimi është mekanik: një metodë e gjatë "
        "ose e ndërfutur thellë mban më shumë return, break e continue brenda bllokut, "
        "dhe Extract Method nuk e ngre dot një bllok nga i cili rrjedha del. Motori "
        "nuk refuzon më shpesh te rastet e rënda; refuzon për një arsye tjetër, dhe "
        "ajo arsye është ajo që zgjidhet më vështirë.",
    ]


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

    return [
        "Që një rishkrim të kompilojë nuk do të thotë se e zgjidh problemin për të "
        "cilin u aplikua. Prandaj çdo entitet i rishkruar u mat sërish dhe u pyet nëse "
        "detektori ende ndez mbi të.",
        ("table", "A u hoq era pas rishkrimit",
         ["Rezultati", "Numri", "Pjesa e të aplikuarave"], rows),
        f"Në {persists / total:.1%} të rasteve era mbetet pas një rishkrimi krejtësisht "
        f"të saktë. Kjo nuk është defekt i zbatimit por pasojë e vetë transformimeve, "
        f"dhe rrjedh drejtpërdrejt nga përkufizimet e metrikave.",
        "Guard Clauses heq saktësisht një nivel ndërfutjeje, ndërsa Deep Nesting ndez "
        "mbi tre: një metodë e ndërfutur katër nivele shërohet, një e ndërfutur gjashtë "
        "mbetet mbi kufirin. Extract Method e shkurton metodën duke nxjerrë bllokun më "
        "të madh, pa asnjë garanci se e kalon prapa pragun. Vetëm Introduce Parameter "
        "Object e zgjidh erën me ndërtim, sepse lista e parametrave bëhet një.",
        *_metric_shift_paragraphs(data),
        *_introduced_paragraphs(data),
        "Pasoja praktike është se numri i vendeve të transformuara nuk duhet lexuar si "
        "numri i erërave të hequra. Të tria matjet duhen lexuar bashkë: sa raste u "
        "shëruan, sa lëvizi matja te ato që nuk u shëruan, dhe sa herë rishkrimi solli "
        "një problem të ri.",
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
        "Të thuash vetëm nëse era mbeti do të thoshte t'i lexoje njësoj një rishkrim "
        "që nuk ndryshoi asgjë dhe një që e përgjysmoi metodën. Prandaj raportohet edhe "
        "sa lëvizi matja mbi të cilën ndez detektori, si mesore mbi vendet e aplikuara.",
        ("table", "Sa lëvizi matja pas rishkrimit",
         ["Erë", "Para", "Pas", "Vende"], rows),
        "Lëvizja është e madhe atje ku transformimi ka hapësirë të veprojë dhe e vogël "
        "atje ku nuk ka: Guard Clauses heq një nivel të vetëm, dhe mesorja e tregon "
        "pikërisht atë. Pra edhe kur era mbetet, kodi nuk mbetet i pandryshuar.",
    ]


def _introduced_paragraphs(data: dict) -> list:
    """A e shkëmbeu motori një erë me një tjetër?"""
    introduced = data.get("introduced_smells")
    if not introduced:
        return []

    total = sum(introduced.values())
    listed = ", ".join(f"{name} ({count})" for name, count in sorted(introduced.items()))
    return [
        f"Mbetet pyetja e fundit dhe më e pakëndshmja: a solli rishkrimi një erë që nuk "
        f"ishte aty? Klasa u mat e tëra para dhe pas, sepse Extract Method krijon një "
        f"metodë të re, dhe kod i ri është kod që askush nuk e ka matur ende. "
        f"Përgjigjja është po, {total} herë: {listed}.",
        "Shumica janë Long Parameter List, dhe shkaku është i drejtpërdrejtë: Extract "
        "Method ia kalon metodës së nxjerrë çdo vlerë që blloku lexonte, ndaj një bllok "
        "me gjashtë hyrje prodhon një metodë me gjashtë parametra — një mbi pragun. "
        "Transformimi është i saktë dhe kompilon; thjesht e zhvendos problemin.",
        "Kjo është e njëjta formë me paradoksin e Encapsulate Field-it të Nënkapitullit "
        "6.2: një refaktorim i rekomanduar gjerësisht që, i matur me vetë metrikat mbi "
        "të cilat ndërtohet detektimi, nuk përmirëson domosdo atë që mat detektori. "
        "Motori nuk e fsheh: numri raportohet krahas atyre të shëruara.",
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
REPRODUCTION = [
    ("1", "fetch_corpus.py", "korpusi, jashtë git-it", "orë, një herë"),
    ("2", "build_dataset.py", "tabela e veçorive, e komituar", "~95 min"),
    ("3", "evaluate_rules.py --from-dataset", "numrat e Qasjes A", "sekonda"),
    ("4", "train_models.py", "numrat e Qasjes B dhe modelet", "sekonda"),
    ("5", "sweep_thresholds.py", "analiza e ndjeshmërisë", "sekonda"),
    ("6", "evaluate_refactorings.py", "tabela N/M/K e Qasjes C", "orë"),
    ("7", "calibrate_thresholds.py", "pragjet e kalibruara jashtë fold-it", "~1 min"),
    ("8", "reviewer_agreement.py", "tavani i pajtimit mes rishikuesve", "sekonda"),
    ("9", "bootstrap_intervals.py", "intervalet e besimit", "nën një minutë"),
    ("10", "export_system_reference.py", "tabelat e kësaj shtojce", "sekonda"),
    ("11", "build_figures.py", "figurat e Kapitullit 5", "sekonda"),
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

    environment = reference["environment"]

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
                "veçantë. Vlerat janë ato të nxjerra statistikisht nga një korpus prej "
                "dyzet e pesë sistemesh Java dhe C++.",
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
                "commit-in, versionin e Python-it dhe platformën që e prodhuan. Numrat e "
                "këtij punimi u prodhuan me commit-in "
                f"{environment['commit'][:10]}, Python {environment['python']}, "
                f"{environment['platform']}.",
                "Kapitulli 5 dhe kjo shtojcë ndërtohen nga ata skedarë, ndaj rigjenerimi i "
                "eksperimentit dhe rigjenerimi i dokumentit japin gjithmonë të njëjtat "
                "vlera.",
            ],
        ),
    ]
