"""Përmbajtja e kapitujve 2 deri 6.

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
            "projekt nuk i provon dot parakushtet e veta. Rrjedhimisht tri nga pesë "
            "transformimet e planifikuara mbeten propozim dhe nuk aplikohen "
            "automatikisht. Kjo nuk është mangësi implementimi por pasojë e "
            "deklaruar e zgjedhjes.",
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
            "Analizuesi nuk zgjidh simbole, ndaj tri nga pesë transformimet e "
            "planifikuara nuk automatizohen. Kjo nuk është mangësi implementimi por "
            "pasojë e drejtpërdrejtë e një zgjedhjeje arkitekturore të deklaruar.",
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
                "Analizë e ndjeshmërisë mbi pragje, e cila tashmë është e mundur në "
                "sekonda falë tabelës së veçorive.",
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
                ("figure", str(FIGURES / "figura_5_shperndarja_e_mostrave.png"),
                 "Figura 5. Shpërndarja e mostrave sipas erës"),
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
                ("table", "Tabela 1. Qasja A kundrejt gjykimit të rishikuesve",
                 ["Erë", "P", "R", "F1", "MCC", "Pozitivë"], rules_rows),
                "Modeli është i njëjtë kudo: precizion i lartë dhe recall i ulët. Kur "
                "strategjitë ndezin kanë kryesisht të drejtë, por i humbin shumicën e "
                "rasteve.",
                "Ky lexim ndryshon kur recall-i ndahet sipas ashpërsisë që caktuan "
                "vetë rishikuesit.",
                ("table", "Tabela 2. Recall-i sipas ashpërsisë",
                 ["Erë", "Recall te major", "Recall te minor"], severity_rows),
                ("figure", str(FIGURES / "figura_2_recall_sipas_ashpersise.png"),
                 "Figura 2. Recall-i sipas ashpërsisë së caktuar nga rishikuesit"),
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
                ("table", "Tabela 3. Modeli më i mirë për çdo erë",
                 ["Erë", "Modeli", "P", "R", "F1", "MCC"], ml_rows),
                f"MCC-ja më e lartë e arritur është {best_mcc:.3f}. Të gjitha vlerat "
                "vijnë nga parashikime jashtë fold-it mbi një ndarje të grupuar sipas "
                "depos, pra përshkruajnë atë që pritet mbi një projekt që modeli nuk e "
                "ka parë kurrë.",
                ("figure", str(FIGURES / "figura_4_rendesia_e_vecorive.png"),
                 "Figura 4. Veçoritë me rëndësi më të lartë, të matura me permutation importance"),
            ],
        ),
        (
            "5.3",
            "Krahasimi i dy qasjeve",
            [
                ("figure", str(FIGURES / "figura_1_mcc_a_vs_b.png"),
                 "Figura 1. MCC për të dyja qasjet"),
                "Qasja B e tejkalon Qasjen A në çdo erë. Por përmbledhja nuk e tregon "
                "se çka kap secila vetëm, ndaj raportohen edhe të katër qelizat bashkë "
                "me koeficientin kappa.",
                ("table", "Tabela 4. Pajtimi mes dy qasjeve",
                 ["Erë", "κ", "Të dyja", "Vetëm A", "Vetëm B", "n"], agreement_rows),
                ("figure", str(FIGURES / "figura_3_pajtimi_a_b.png"),
                 "Figura 3. Mostrat e shënuara nga secila qasje"),
                "Kolona «vetëm B» tejkalon «vetëm A» në çdo erë, shpesh me një rend "
                "madhësie: modeli pothuajse e përfshin rregullin. Përjashtimi është "
                "Feature Envy, ku rregulli kap një numër të krahasueshëm rastesh që "
                "modeli i humb.",
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
                ("table", "Tabela 5. Sa lëviz MCC-ja kur zhvendoset një prag",
                 ["Erë", "Pragu", "Te vlera e botuar", "Brezi", "Amplituda"], sweep_rows),
                ("figure", str(FIGURES / "figura_6_ndjeshmeria_e_pragjeve.png"),
                 "Figura 6. Ndjeshmëria e MCC-së ndaj zhvendosjes së pragjeve"),
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
                "kjo mbetet punë e ardhshme.",
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
        ("table", "Tabela 6. Rezultati i motorit të refaktorimit",
         ["", "Numri", "Pjesa"], rows),
        "Shpërndarja e arsyeve të refuzimit është vetë rezultat: ajo tregon çfarë e "
        "pengon automatizimin, dhe jo se ku dështon zbatimi.",
        ("table", "Tabela 7. Pse u refuzuan",
         ["Arsyeja", "Numri", "Pjesa e vendeve"], refusals),
        ("table", "Tabela 8. Verifikimi i atyre që u aplikuan",
         ["Verdikti", "Numri", "Pjesa e të aplikuarave"], verdicts),
        f"Nga {applied} rishkrime, {broken} futën një gabim që nuk ishte aty më parë "
        f"({share:.2%}). Pjesa tjetër ose kompiloi, ose nuk shtoi asnjë lloj të ri "
        "gabimi kundrejt skedarit origjinal.",
    ]
