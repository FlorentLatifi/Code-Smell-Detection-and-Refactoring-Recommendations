# Regjistri i vendimeve

Çdo vendim teknik me pasoja, i shkruar kur merret. Ky skedar është lënda e parë e
**Kapitullit 4 (Metodologjia)**; mbrojtja e një zgjedhjeje tre muaj më vonë, nga
kujtesa, është ku humbin pikët.

Formati: konteksti → vendimi → alternativat → pasojat. Një vendim i ndryshuar nuk
fshihet; i shtohet një hyrje e re që e zëvendëson, sepse edhe ndryshimi i mendjes
është metodologji.

| # | Vendimi | Data | Statusi |
|---|---|---|---|
| VD-01 | Java si gjuhë e vetme e analizuar | 2026-08-25 | aktiv |
| VD-02 | tree-sitter si front-end analizues | 2026-08-25 | aktiv |
| VD-03 | Pa LLM në rrugën e produktit | 2026-08-25 | aktiv |
| VD-04 | Tri qasje të pavarura dhe të krahasueshme | 2026-08-25 | aktiv |
| VD-05 | MLCQ si e vërtetë bazë | 2026-08-25 | aktiv |
| VD-06 | Ashpërsia derivohet nga teprica, në shkallën e MLCQ | 2026-08-25 | aktiv |
| VD-07 | Pragjet të centralizuara dhe të citueshme | 2026-08-25 | aktiv |
| VD-08 | Detektorët kthejnë kushtet, jo boolean | 2026-08-25 | aktiv |
| VD-09 | Large Class e ndarë nga God Class | 2026-08-25 | aktiv |
| VD-10 | Python për backend-in që analizon Java | 2026-08-25 | aktiv |
| VD-11 | Refuzimi është rezultat i saktë i refaktorimit | 2026-08-25 | aktiv |
| VD-12 | Ndarje sipas depos në vlerësimin ML | 2026-08-25 | aktiv |
| VD-13 | Punimi gjenerohet me kod, jo formatohet me dorë | 2026-08-25 | aktiv |
| VD-14 | Portë cilësie e detyrueshme para shkrimit të kodit kritik | 2026-08-25 | aktiv |
| VD-15 | Agregimi i etiketave: mesatare e rrumbullakosur lart, e ndërrueshme | 2026-08-25 | aktiv |
| VD-16 | Korpusi me depo të plota, jo me skedarë të veçuar | 2026-08-25 | aktiv |
| VD-17 | Shtigjet e gjata të Windows-it zgjidhen në kod, jo në sistem | 2026-08-25 | aktiv |
| VD-18 | Fushat që Java i deklaron në heshtje maten si fusha | 2026-08-25 | aktiv |
| VD-19 | Përputhja MLCQ↔entitet ankorohet te rreshtat, verifikohet me emrin | 2026-08-25 | aktiv |

---

### VD-01: Java si gjuhë e vetme e analizuar

**Konteksti.** Detektimi i code smells varet nga metrika objekt-orientuara që
supozojnë klasa, trashëgimi dhe fusha.

**Vendimi.** Analizohet vetëm Java.

**Alternativat.** Mbështetje shumë-gjuhëshe; Python si gjuhë e dytë.

**Pasojat.** Metrikat CK zbatohen drejtpërdrejt pa përshtatje; MLCQ është
tërësisht Java, pra e vërteta bazë përputhet me objektin e analizës; verifikimi
me `javac` bëhet i mundur. Kufizim: përgjithësimi te gjuhët jo-OO nuk pretendohet
dhe raportohet te "kufizimet".

---

### VD-02: tree-sitter si front-end analizues

**Konteksti.** Nevojitet një pemë analize e saktë për Java-n moderne, pa varësi
nga JVM-ja gjatë analizës.

**Vendimi.** `tree-sitter` + `tree-sitter-java`.

**Alternativat.** `javalang` (Python, i pambështetur mirë për sintaksën pas Java 8);
JavaParser përmes një procesi Java (kërkon JVM dhe një urë ndër-procesore).

**Pasojat.** Mbulon record, sealed types, switch expressions dhe lambda; analiza
nuk kërkon JVM. Kompromis i pranuar: tree-sitter nuk zgjidh simbole, prandaj
parser-i regjistron vetëm fakte sintaksore dhe interpretimi bëhet te `metrics/`,
ku klasa deklaruese njihet. Kjo mjafton për të gjitha strategjitë e Lanza &
Marinescu dhe shmang ndërtimin e një sistemi tipash.

---

### VD-03: Pa LLM në rrugën e produktit

**Konteksti.** Rekomandimet e refaktorimit mund të gjenerohen nga një model
gjuhësor. API-të me pagesë janë të përjashtuara (kosto), dhe një model lokal mbi
Ryzen 7 5825U pa GPU të dedikuar është praktikisht i papërdorshëm.

**Vendimi.** Refaktorimet janë transformime deterministike mbi AST, sipas
katalogut të Fowler-it.

**Alternativat.** API e paguar; model lokal i kuantizuar; qasje hibride.

**Pasojat.** Dalja është e riprodhueshme dhe e verifikueshme me `javac`: një
pretendim empirik shumë më i fortë se "modeli propozoi diçka që duket mirë".
Komisioni mund ta ekzekutojë sistemin pa asnjë çelës. Kufizim: mbulohen vetëm
transformimet e implementuara, jo çdo rishkrim i mundshëm.

---

### VD-04: Tri qasje të pavarura dhe të krahasueshme

**Konteksti.** Një punim diplome ka nevojë për një pyetje kërkimore, jo vetëm për
një vegël.

**Vendimi.** Tri shtylla: (A) rregulla me metrika, (B) machine learning mbi MLCQ,
(C) motor refaktorimi. A dhe B prodhojnë dalje të krahasueshme mbi të njëjtin
input.

**Alternativat.** Vetëm rregulla (i thjeshtë por pa kontribut); vetëm ML (kuti e
zezë, pa gjurmueshmëri).

**Pasojat.** Krahasimi A vs B është kontributi kryesor empirik. Kërkon që të dyja
qasjet të ndajnë të njëjtën shkallë ashpërsie dhe të njëjtat entitete, prandaj
VD-06 dhe përputhësi i Fazës 1.

---

### VD-05: MLCQ si e vërtetë bazë

**Konteksti.** ML-ja kërkon etiketa; vlerësimi i Qasjes A kërkon një referencë të
pavarur nga vetë rregullat tona.

**Vendimi.** MLCQ (Madeyski & Lewowski, 2020): mostra Java të etiketuara nga
zhvillues profesionistë, për Blob, Data Class, Long Method dhe Feature Envy.

**Alternativat.** Etiketim manual (i pamundur në shkallë brenda afatit);
dataset-e sintetike (jo relevante industrialisht); dalja e një vegle tjetër si
referencë (do të matte pajtimin me atë vegël, jo saktësinë).

**Pasojat.** Katër smells kanë vlerësim sasior; katër të tjerët e implementuar
(Large Class, Brain Method, Long Parameter List, Deep Nesting) raportohen vetëm
në mënyrë përshkruese, dhe kjo thuhet hapur. MLCQ nuk përmban kod; korpusi duhet
materializuar nga GitHub, me humbjen e pashmangshme të depove të fshira, e cila
raportohet si kufizim i studimit.

---

### VD-06: Ashpërsia derivohet nga teprica, në shkallën e MLCQ

**Konteksti.** Ashpërsia e caktuar në mënyrë arbitrare ("God Class = gjithmonë
kritike") nuk mbrohet dot.

**Vendimi.** `Severity` merr vlerat `minor/major/critical` (pikërisht shkalla e
MLCQ) dhe llogaritet si mesatare e tepricës mbi pragje, e kufizuar në 5× që një
metrikë ekstreme të mos e ngrejë vetëm një rast të butë.

**Alternativat.** Ashpërsi fikse për smell; ashpërsi e mësuar nga ML-ja.

**Pasojat.** Dalja e rregullave krahasohet me etiketat manuale pa hap përkthimi.
Kufizimi 5× dhe kufijtë 1.5/2.5 janë zgjedhje kalibrimi që duhet t'i nënshtrohen
analizës së ndjeshmërisë në Fazën 5.

---

### VD-07: Pragjet të centralizuara dhe të citueshme

**Konteksti.** Pragjet e shpërndara nëpër kod nuk mund as të mbrohen as të
variohen.

**Vendimi.** Të gjitha në `detectors/thresholds.py`, si `dataclass` e ngrirë, me
burimin e cituar pranë secilës vlerë.

**Pasojat.** Analiza e ndjeshmërisë bëhet programatikisht duke krijuar instanca
alternative; ngrirja pengon që një fshirje ta ndotë bazën me të cilën krahasohet.

---

### VD-08: Detektorët kthejnë kushtet, jo boolean

**Konteksti.** Një vegël që thotë vetëm "kjo klasë ka erë" nuk ndihmon askënd.

**Vendimi.** Çdo `Smell` mban listën e `Condition`-eve me metrikën, operatorin,
pragun dhe vlerën e matur.

**Pasojat.** Ndërfaqja shpjegon *pse*; punimi raporton cila klauzolë e mbajti
detektimin; ashpërsia rrjedh nga matja. Kosto: pak më shumë kod për detektor,
plotësisht e justifikuar.

---

### VD-09: Large Class e ndarë nga God Class

**Konteksti.** Të dyja kanë të bëjnë me madhësinë e klasës.

**Vendimi.** Raportohen veçmas: God Class kërkon edhe dëshminë e mungesës së
kohezionit (WMC ∧ TCC ∧ ATFD), Large Class vetëm madhësinë (CLOC ∨ NOM).

**Pasojat.** Një klasë e madhe por kohezive nuk etiketohet si God Class. Në
vlerësimin ndaj MLCQ-së, vetëm God Class krahasohet me etiketën *Blob*; Large
Class trajtohet si sinjal i veçantë, jo si i njëjti smell.

---

### VD-10: Python për backend-in që analizon Java

**Konteksti.** Sistemi analizon Java; nuk rrjedh që duhet shkruar në Java.

**Vendimi.** Python 3.13 për analizën, ML-në dhe API-në.

**Alternativat.** Java me JavaParser dhe Spring (ekosistemi vendas i analizës);
hibrid Java-analizë + Python-ML.

**Pasojat.** scikit-learn dhe pandas janë të disponueshme drejtpërdrejt, pa urë
ndër-gjuhëshe, vendimtare për Shtyllën B. `javac` përdoret vetëm si nënproces
verifikimi, që është një sipërfaqe e vogël dhe e kontrolluar.

---

### VD-11: Refuzimi është rezultat i saktë i refaktorimit

**Konteksti.** Një transformim mbi kod të huaj mund ta prishë atë kur parakushtet
nuk verifikohen.

**Vendimi.** Kur një parakusht nuk provohet nga pema e analizës, transformimi
kthen "e paaplikueshme" me arsye, dhe kjo numërohet në rezultate.

**Alternativat.** Provo gjithsesi dhe kthehu prapa nëse `javac` dështon (rrezik
ndryshimesh që kompilojnë por ndryshojnë sjelljen).

**Pasojat.** Shkalla e aplikimit do të jetë më e ulët se e një vegle agresive,
por çdo transformim i aplikuar është i mbrojtshëm. Shpërndarja e arsyeve të
refuzimit bëhet vetë një rezultat interesant i punimit.

---

### VD-12: Ndarje sipas depos në vlerësimin ML

**Konteksti.** MLCQ përmban shumë mostra nga e njëjta depo, me stil dhe konventa
të përbashkëta.

**Vendimi.** `GroupKFold` me depon si grup; asnjë depo nuk shfaqet njëkohësisht
në trajnim dhe testim. Farë e fiksuar.

**Alternativat.** Ndarje e rastësishme sipas rreshtave (jep numra dukshëm më të
mirë, dhe të pavlefshëm).

**Pasojat.** Rezultate më modeste por të vërteta, që matin përgjithësimin te një
projekt i panjohur; pikërisht ai është përdorimi real i veglës.

---

### VD-13: Punimi gjenerohet me kod, jo formatohet me dorë

**Konteksti.** Shablloni i UBT-së ka tri regjime numërimi faqesh, rregulla fonti
për nivel titulli dhe hapësirë rreshtash minimale, të lehta për t'u prishur me
redaktim manual.

**Vendimi.** `docs/thesis/build_thesis.py` e ndërton dokumentin me `python-docx`;
përmbajtja qëndron e ndarë nga paraqitja.

**Pasojat.** Përputhshmëria me shabllonin rifitohet me një ekzekutim. Kufizim i
rëndësishëm: pas dorëzimit të skeletit, redaktimi kalon në Word dhe rikthimi i
skriptit e mbishkruan skedarin, pra në atë pikë skripti dhe dokumenti duhet të
konsiderohen të shkëputur, ose përmbajtja të mbahet e sinkronizuar në `CONTENT`.

---

### VD-14: Portë cilësie e detyrueshme para shkrimit të kodit kritik

**Konteksti.** Kodi kryesor (motori i refaktorimit, harness-i i vlerësimit) ende
nuk është shkruar. Vendosja e kontrolleve automatike *pasi* të shkruhet do të
thoshte t'i zbatosh mbi disa mijëra rreshta njëherësh, çka zakonisht përfundon
me çaktivizimin e tyre.

**Vendimi.** `ruff` (lint + format), `mypy --strict`, `pytest-cov` dhe GitHub
Actions vendosen para Fazës 1. Paralajmërimet e testeve trajtohen si gabime.
Python-i pinohet në 3.13 edhe në CI.

**Alternativat.** Vetëm teste (linter-i dhe tipizimi shtohen më vonë ose kurrë);
`mypy` jo-strikt për të shmangur anotimet.

**Pasojat.** Kostoja u pagua menjëherë dhe u kthye po aq shpejt: kontrollet
zbuluan një defekt që rrëzonte tërë analizën e një projekti (`Node.text` mund të
jetë `None`), një element të dyfishtë në filtrin e LOC-ut, dhe faktin që `cli.py`,
pikënisja e eksperimenteve, nuk kishte asnjë test. Kufizim i pranuar: `ruff format`
i shpërthen listat e kolonave CSV një-për-rresht, çka është më pak e lexueshme se
rreshtimi tabelar; pranohet si kompromis dhe pastrohet në Fazën 4, kur API-ja t'i
ripërdorë ato kolona si konstante të përbashkët.

Pinimi i Python 3.13 nuk është pedanteri: një metrikë që ndryshon vlerë në heshtje
mes versioneve të interpretuesit do t'i bënte të pariprodhueshme numrat e publikuar.

---

### VD-15: Agregimi i etiketave: mesatare e rrumbullakosur lart, e ndërrueshme

**Konteksti.** MLCQ nuk publikon etiketa, publikon **rishikime**. Çdo mostër u
vlerësua në mënyrë të pavarur nga disa zhvillues profesionistë, dhe ata nuk
pajtohen aq shpesh sa kjo të mbetet detaj teknik: nga 4747 mostra me më shumë se
një rishikues, **25.9% mbajnë më shumë se një ashpërsi**, dhe **25.6% nuk pajtohen
as për pyetjen binare** nëse era ekziston fare. Kthimi i rishikimeve në një etiketë
të vetme e përcakton vetë të vërtetën bazë ndaj së cilës matet gjithçka.

**Vendimi.** Agregimi është strategji e deklaruar dhe e ndërrueshme
(`Aggregation`), me `MEAN` si parazgjedhje: mesatarja e rangjeve ordinale,
e rrumbullakosur **gjysma lart**.

**Alternativat.** Vota e shumicës: e papërdorshme këtu, sepse rasti dominues
janë saktësisht **dy** rishikues (3511 nga 4747 mostra), ku një mospajtim nuk ka
shumicë. `MAX` (mjafton një rishikues) fryn pozitivet; `MIN` i fsheh; `UNANIMOUS`
i heq krejt mospajtimet dhe humb 26% të të dhënave.

**Pasojat.** Barazimi 0.5 (p.sh. `none` + `minor`) shkon te etiketa më e rëndë,
pra një erë që një rishikues e pa nuk fshihet. Kujdes teknik i regjistruar:
`round()` i Python-it është rrumbullakosje bankare dhe do ta çonte barazimin
**poshtë**, drejt "pa erë", e kundërta e qëllimit; prandaj llogaritja bëhet
shprehimisht me `+ 0.5`. Të katër strategjitë duhet të raportohen në analizën e
ndjeshmërisë së Fazës 5, sepse kjo zgjedhje lëviz çdo numër të Kapitullit 5.

---

### VD-16: Korpusi me depo të plota, jo me skedarë të veçuar

**Konteksti.** MLCQ jep depo, commit, shteg dhe rang rreshtash, jo kod. Zgjidhja
më e lirë do të ishte të merret vetëm skedari ku ndodhet mostra: 4560 skedarë në
vend të 522 depove.

**Vendimi.** Shkarkohet pema e plotë e burimit në commit-in e saktë, duke ruajtur
vetëm skedarët `.java`.

**Alternativat.** Vetëm skedari i mostrës; vetëm paketa përreth; një nënbashkësi
depove të zgjedhura sipas madhësisë.

**Pasojat.** ATFD, DIT, NOC dhe CBO përkufizohen kundrejt tipave **të projektit**.
Në një "projekt" me një skedar, ATFD-ja do të numëronte vetëm qasjet brenda po atij
skedari, do të binte pothuajse në zero, dhe God Class me Feature Envy nuk do të
aktivizoheshin pothuajse kurrë. Recall-i i matur do të përshkruante korpusin, jo
detektorët, një artefakt që do ta zhvlerësonte tërë Kapitullin 5.

Kostoja u verifikua para vendimit, jo u hamendësua. Madhësia e depove sipas GitHub
API-së projekton ~125 GB, por ai numër përfshin tërë historinë; tarball-i i një
commit-i të vetëm doli **2–18%** e saj, pra projeksioni real është rreth **12–15 GB**
shkarkim dhe shumë më pak në disk. Prandaj nuk u desh të sakrifikohet mbulimi.

Shkarkimi renditet sipas numrit të mostrave për depo, që një ekzekutim i ndërprerë
të lërë gjithsesi nënbashkësinë më të dobishme. Depot që nuk zgjidhen më
regjistrohen në `manifest.json` dhe raportohen si kufizim i studimit.

---

### VD-17: Shtigjet e gjata të Windows-it zgjidhen në kod, jo në sistem

**Konteksti.** Nxjerrja e korpusit dështoi me `FileNotFoundError` mbi skedarë që
sapo ishin shkruar. Shkaku: `LongPathsEnabled = 0` në këtë makinë, rrënja e
projektit zë 97 karaktere, dhe pemët e paketave Java shkojnë deri në 174, pra
mbi kufirin 260 të Windows-it. Shtegu më i gjatë real i vërejtur: **278 karaktere**.

**Vendimi.** Çdo qasje në sistemin e skedarëve nën rrënjën e korpusit kalon nëpër
`long_path()`, që shton prefiksin `\?\`.

**Alternativat.** Aktivizimi i `LongPathsEnabled` në regjistër (kërkon të drejta
administratori dhe e bën korpusin të riprodhueshëm vetëm në një makinë të
konfiguruar ashtu); zhvendosja e projektit në një shteg të shkurtër (e brishtë:
mjafton një pemë pak më e thellë për ta rikthyer problemin).

**Pasojat.** Sistemi punon në çdo makinë Windows pa konfigurim paraprak. Mënyra e
dështimit ishte e heshtur dhe mashtruese: `is_file()` thjesht kthen `False` mbi
një skedar që ekziston, çka do të kishte nënvlerësuar mbulimin e të vërtetës bazë
pa dhënë asnjë gabim; prandaj ekziston një test i dedikuar me shteg mbi 260
karaktere.

---

### VD-18: Fushat që Java i deklaron në heshtje maten si fusha

**Konteksti.** Gjatë ndërtimit të përputhësit MLCQ↔entitet dolën mostra që nuk
lidheshin me asnjë metodë. Shkaku nuk ishte përputhësi. Te tree-sitter, anëtarët
e një `enum`-i nuk qëndrojnë drejtpërdrejt në `enum_body`, por brenda një nyjeje
të vetme `enum_body_declarations`, dhe parser-i ynë lexonte vetëm fëmijët e
drejtpërdrejtë. Rrjedhimisht **çdo enum në korpus dilte me zero fusha dhe zero
metoda**: NOM, NOF, WMC, LCOM dhe TCC të gjitha zero, dhe asnjë detektim i
mundshëm. E njëjta klasë problemi doli edhe dy herë të tjera. Fushat e një
`interface`-i vijnë si `constant_declaration`, jo `field_declaration`, ndërsa
komponentët e një `record`-i qëndrojnë në kokën e deklarimit, jo në trup.

**Vendimi.** Të treja lexohen si fusha, me modifikuesit që gjuha ua jep pa i
shkruar: konstantet e enum-it janë `public static final` të tipit të vetë
enum-it (JLS 8.9.3), fushat e interface-it `public static final` (JLS 9.3), dhe
komponentët e record-it `private final` (JLS 8.10.3).

**Alternativat.** Të lexohen vetëm metodat e enum-it dhe konstantet të lihen
jashtë, por atëherë `enum E { A, B }` dhe klasa ekuivalente e shkruar me dorë
maten ndryshe pa asnjë arsye. Ose të mbetej gjendja e mëparshme dhe mostrat
brenda enum-eve të hiqeshin nga vlerësimi, çka do ta ulte mbulimin dhe do t'i
linte metrikat e çdo enum-i të gabuara edhe në vetë produktin.

**Pasojat.** Numri i mostrave të lidhura u rrit nga 1257 në 1666 mbi të njëjtin
korpus, dhe dështimet e emrit ranë nga 14 në 3. `is_constant` mbetet vendimtar:
duke qenë se konstantet janë të tilla, NOPA dhe WOC nuk preken, pra detektori i
Data Class-it nuk fillon të shënojë enum-e. Tipi i një konstanteje enum është
vetë enum-i, që CBO-ja tashmë e përjashton si vetë-referencë. Metrikat e
enum-eve, interface-ave dhe record-eve **ndryshojnë vlerë** ndaj gjendjes së
mëparshme, por asnjë numër nuk ishte publikuar ende dhe vlera e mëparshme ishte
zero, pra kjo është korrigjim defekti dhe jo ricaktim pragu.

Mbetet e njohur dhe jashtë fushëveprimit: metodat brenda klasave anonime
(`new Runnable() { ... }`) nuk modelohen. Janë 7 nga 4295 mostrat e disponueshme.

---

### VD-19: Përputhja MLCQ↔entitet ankorohet te rreshtat, verifikohet me emrin

**Konteksti.** Plani e quajti këtë hapin me rrezikun e vërtetë të Fazës 1. MLCQ
e identifikon entitetin me `code_name`, dhe ajo fushë nuk ka një format por
katër: `a.b.C` për tipat, `a.b.C#m` për shumicën e metodave, `a.b.C.m` për çdo
konstruktor dhe për 333 metoda të zakonshme përveç tyre, secili opsionalisht i
ndjekur nga `" int|String"`. Katër rreshta kanë edhe segment tipi bosh
(`a.b..m`). Mbingarkesat dhe klasat e brendshme dukeshin si problem që kërkon
zgjidhje simbolesh.

**Vendimi.** Ankora është **rangu i rreshtave**, ndërsa emri i thjeshtë përdoret
vetëm si verifikim. Përputhja pranohet kur `start_line`, `end_line` dhe emri i
fundit përputhen të tria; çdo mospërputhje raportohet si `MatchOutcome` i veçantë
dhe nuk detyrohet të bëhet përputhje.

Vendimi u mor pas matjes, jo para saj. Mbi mostrat e materializuara, rangjet e
MLCQ-së përputhen saktësisht me parser-in për **791 nga 791 klasa** dhe **871 nga
875 metoda**, ndërsa emrat përputhen shumë më rrallë.

**Alternativat.** Përputhje sipas emrit të plotë me zgjidhje simbolesh, e cila
kërkon pikërisht zgjidhësin që `ENGINEERING.md` §2 e ndalon te `parsing/`, për një
përfitim prej rreth 0.3%. Ose përputhje sipas emrit me tolerancë rreshtash, e
cila pranon mbingarkesën fqinje kur emri përsëritet: gabimi që prodhon numra
plotësisht të besueshëm dhe plotësisht të rremë.

**Pasojat.** Dy ambiguitetet që plani i listoi si rreziqe zhduken pa kosto, sepse
dy mbingarkesa nuk fillojnë dot në të njëjtin rresht, as një klasë e brendshme
dhe ajo që e mbyll. Rasti kur vërtet fillojnë në një rresht raportohet si
`AMBIGUOUS`. Mbi korpusin e plotë (499 depo nga 522, me 4295 mostra që kanë burim):
**99.8%** lidhen me entitetin e tyre, 4286 nga 4295. I njëjti raport doli edhe kur
korpusi ishte një e katërta e kësaj, çka tregon se numri mat përputhësin dhe jo
gjendjen e shkarkimit. Dështimet janë 7 metoda brenda klasave anonime dhe 2 nga
një skedar i vetëm që gramatika nuk e lexon dot:
`Hamlet.java` i Hadoop-it përdor `_` si emër metode, i palejueshëm që nga Java 9.
Prandaj `CompilationUnit` mban `has_syntax_errors`; pa të, kufizimi i front-end-it
tonë do t'i ngarkohej të vërtetës bazë.

---

### VD-20: Depot e zhvendosura ndiqen, por vetëm kur commit-i zgjidhet

**Konteksti.** 23 nga 522 depot e MLCQ-së kthenin HTTP 404 dhe kushtonin 406
mostra. Humbja nuk ishte e rastësishme: 15 prej tyre ishin `eclipse/*` dhe vetëm
ato bartnin 337 mostra. Një humbje e përqendruar në një organizatë nuk është
thjesht korpus më i vogël, është **anshmëri sistematike**: kodi i Eclipse-it do të
zhdukej pothuajse tërësisht nga vlerësimi.

**Vendimi.** Ndiqet zhvendosja, por një depo e re pranohet **vetëm nëse zgjidhet
commit-i i saktë që publikoi MLCQ**. Harta qëndron si konstante e komituar te
`evaluation/corpus.py::REPOSITORY_MOVES`.

Arsyeja pse kjo nuk e cenon të vërtetën bazë është një veti e git-it, jo një
supozim yni: **commit-i emërtohet me SHA-1 të përmbajtjes së tij**. Nëse hash-i
zgjidhet te vendndodhja e re, pema që ai emërton është bit-për-bit e njëjtë me atë
që panë rishikuesit, pavarësisht URL-së nga ku erdhi. Prandaj kriteri i pranimit
është verifikim, jo besim.

**Alternativat.** Ta pranonim depon me emër të ngjashëm pa verifikuar commit-in:
kjo do të fuste kod *të ndryshëm* nën të njëjtën etiketë, gabimi më i keq i
mundshëm në një vlerësim. Ose ta raportonim mbulimin 90% si kufizim dhe të mos
bënim asgjë: e ndershme, por e pranon anshmërinë ndaj Eclipse-it pa nevojë.

**Pasojat.** 13 depo u rikuperuan me **254 mostra**; mbulimi shkon nga 90.0% në
95.4%. Dy shkaqe i shpjegojnë të gjitha: Eclipse Foundation e ndau organizatën e
vetme `eclipse` në organizata për projekt (çka e humb ridrejtimin e vetë GitHub-it),
dhe `epam/DLab` iu dhurua Apache-s dhe u riemërtua. Depot ku commit-i **nuk** u
zgjidh nuk u zëvendësuan me hamendje: mbeten 10 depo dhe 152 mostra (3.2%) të
humbura përfundimisht, dhe ky numër hyn në punim si kufizim i studimit.

Zhvendosja prek vetëm burimin e shkarkimit. `repo_dirname` mbetet i lidhur me
identitetin që publikoi MLCQ, prandaj asnjë shifër e publikuar dhe asnjë përputhje
nuk varet nga harta; kjo veti mbrohet me test.

---

### VD-21: LOC-u është numërim logjik, me një implementim të vetëm

**Konteksti.** Plani e mbante hapur pyetjen nëse rreshtat si `};` duhet të
përjashtoheshin nga LOC-u. Kontrolli i kodit nxori diçka më të rëndë se pyetja:
ekzistonin **dy implementime** të "lines of code" dhe ato kishin devijuar.
`java_parser.loc()` (MLOC) përjashtonte `{`, `}` dhe `});`; `calculator._class_loc()`
(CLOC) përjashtonte vetëm `{` dhe `}`. Pra një metodë dhe klasa që e mban atë e
matnin të njëjtin burim me rregulla të ndryshme, ndërsa të dyja ushqenin detektorë
madhësie.

**Vendimi.** Një implementim i vetëm, `parsing.java_parser.effective_loc`, i
përdorur edhe nga MLOC edhe nga CLOC, me rregull të parimtë në vend të një liste
formash: **një rresht i përbërë vetëm nga ndarësa strukturorë (`{}()[];,`) nuk
është pohim dhe nuk numërohet.** Ky është dallimi që Park (1992, SEI
CMU/SEI-92-TR-020) bën mes rreshtave fizikë dhe pohimeve logjike.

**Alternativat.** Ta zgjeronim listën me `};` dhe `});`: e njëjta qasje ad-hoc që
sapo kishte devijuar, dhe që do të devijonte prapë te forma e parë e paparashikuar
(`}));` ekziston vërtet në korpus). Ose të mos preknim asgjë: kjo do ta linte
MLOC-un dhe CLOC-un të papajtueshëm në çdo numër të Kapitullit 5.

**Pasojat.** Ndikimi u mat para se të ndryshohej kodi. Në një mostër prej 30 depove
(1 349 531 rreshta jo-bosh), rregulli i ri shton 0.32% rreshta të përjashtuar, të
përqendruar te `});` (1615), `};` (1311) dhe `);` (533). Në fikstuarat e testeve
ndikimi është **zero**, prandaj asnjë pritshmëri ekzistuese e derivuar me dorë nuk
u riderivua — një ndryshim në ato vlera do të kishte kërkuar rinumërim me dorë,
kurrse rregullim të vlerës që të kalojë testi (`ENGINEERING.md` §5). Rregulli i ri
është fiksuar me teste të veta, përfshirë rastin `} else {`, që nuk guxon të bjerë.

---

### VD-22: `blob` krahasohet me God Class, madhësia raportohet si variant

**Konteksti.** MLCQ jep të vërtetë bazë për `blob`, ndërsa VD-09 i ndau
qëllimisht God Class (strategjia e Lanza & Marinescu: WMC, TCC, ATFD) nga Large
Class (vetëm madhësia: CLOC, NOM). Kundër cilës prej tyre matet `blob`?

**Vendimi.** Matja parësore është kundër **God Class** të vetëm. Bashkimi
`GodClass ∪ LargeClass` raportohet si variant ndjeshmërie, jo si rezultat kryesor.

Arsyeja është se pyetja që punimi i bën vetes duhet të jetë e përgjigjshme:
*sa mirë e riprodhon një strategji e publikuar gjykimin e zhvilluesve profesionistë?*
Bashkimi nuk është strategji e publikuar, është konstrukt yni, dhe si i tillë i
takon kolonës së variantit.

**Alternativat.** Bashkimi si matje parësore: ka gjasa të ngrejë recall-in, por
shkrin dy detektorë që VD-09 i ndau me arsye dhe e bën numrin të pakrahasueshëm me
literaturën. Ose vetëm Large Class: e braktis fare strategjinë që projekti e
implementoi.

**Pasojat.** Tabela e Kapitullit 5 mban dy rreshta për `blob`. Dallimi mes tyre
është vetë një gjetje: tregon sa nga ajo që rishikuesit e quajnë "blob" shpjegohet
me madhësi të thjeshtë dhe sa kërkon kushtin e kohezionit. Për tri erërat e tjera
harta mbetet një-me-një; `long method` s'ka nevojë për variant sepse Brain Method
(LOC > 35) është nënbashkësi e rreptë e Long Method (LOC > 30).

---

### VD-23: Tabela e veçorive ndërtohet një herë dhe komitohet

**Konteksti.** Matja e korpusit kushton ~95 minuta: 690 mijë skedarë `.java`, të
gjithë të domosdoshëm sepse ATFD, CBO, DIT dhe TCC përcaktohen kundrejt tipave të
tjerë të projektit (VD-16). Tri gjëra kanë nevojë për saktësisht të njëjtat matje:
trajnimi i Qasjes B, fshirja e pragjeve e Kapitullit 5, dhe ripikëzimi i Qasjes A
pas çdo ndryshimi në detektorë. Me dizajnin e mëparshëm secila do ta paguante
koston nga e para.

**Vendimi.** Një skript i vetëm, `build_dataset.py`, e bën kalimin e shtrenjtë dhe
shkruan `data/results/mlcq_dataset.csv`: një rresht për mostër, me etiketat e
rishikuesve pranë 26 metrikave të matura. Skedari **komitohet**.

Pragjet nuk hyjnë fare në atë kalim — ato veprojnë vetëm në detektim — ndaj
fshirja e tyre bëhet duke rirendur detektorët mbi rreshtat e ruajtur. Përveç
metrikave, rreshti mban edhe `kind`, `is_constructor` dhe `is_accessor`, të vetmet
fusha jo-metrike që rregullat lexojnë; pra rreshti përmban gjithçka që detektori
sheh.

**Alternativat.** Rillogaritja për çdo eksperiment: e ndershme por e pamundur në
praktikë, sepse një fshirje me k konfigurime do të kushtonte k×95 minuta dhe
thjesht nuk do të bëhej. Cache binar (pickle/parquet): më i shpejtë por i palexueshëm
nga një anëtar komisioni dhe i lidhur me versionin e bibliotekës.

**Pasojat.** Kushti i riprodhueshmërisë forcohet: çdo numër i Qasjes B dhe i
analizës së ndjeshmërisë rigjenerohet nga një CSV prej ~2 MB, pa korpusin 4.4 GB
dhe pa 95 minutat. Në këmbim, tabela duhet rindërtuar sa herë ndryshon një metrikë
ose parser-i, dhe ai rindërtim duhet kujtuar; prandaj `test_dataset` dështon nëse
kalkulatori prodhon një metrikë që tabela nuk e ka.

---

### VD-24: Katër modele, pa rrjeta neurale, me baseline të detyrueshëm

**Konteksti.** Qasja B duhet të jetë e krahasueshme me Qasjen A dhe e mbrojtshme
para komisionit, jo thjesht e saktë.

**Vendimi.** Katër modele: klasifikuesi i shumicës, regresioni logjistik, Random
Forest dhe Gradient Boosting. Pa rrjeta neurale.

Baseline-i i shumicës **raportohet gjithmonë**. Mbi një bashkësi ku 78% e
etiketave janë `none`, një F1 mbresëlënës mund të arrihet pa mësuar asgjë, dhe i
vetmi mjet që e dallon këtë është të parit se sa merr parashikimi i klasës
shumicë mbi po atë ndarje.

Modelet që dinë të shprehin peshë klase marrin `class_weight="balanced"`.
Mbi-mostrimi i pakicës do t'i dyfishonte rreshtat përtej kufirit të fold-it dhe do
ta prishte në heshtje grupimin e VD-12.

Modelet e nivelit të metodës shohin edhe metrikat e klasës që i mban. Feature Envy
është pikërisht pohim për **marrëdhënien** mes një metode dhe klasës së saj, dhe
një metodë e gjatë brenda një God Class nuk është e njëjta vëzhgim me një brenda
një ndihmësi të vogël.

**Alternativat.** Një rrjetë neurale: dataset-i është i vogël, veçoritë tabelare,
dhe interpretueshmëria vlen më shumë se një pikë F1 — komisioni do të pyesë *pse*
ndezi modeli. Vetëm metrikat e metodës për erërat e metodave: e thjeshtë, por e bën
Feature Envy të pashprehshme.

**Pasojat.** Rëndësia e veçorive matet me permutation importance mbi fold-in e
mbajtur jashtë, jo me rëndësinë e papastërtisë që një pyll e jep falas: kjo e fundit
anon nga veçoritë me kardinalitet të lartë, pra nga çdo numërim i pakufizuar si CLOC
ose WMC, dhe pikërisht ai anim do ta bënte të pakuptimtë pyetjen nëse ML-ja zgjodhi
metrikat që përdorin strategjitë e Lanza & Marinescu.

---

### VD-25: A dhe B piketohen nga i njëjti kod

**Konteksti.** Krahasimi A kundrejt B është një nga kontributet e punimit. Nëse
secila qasje e llogarit vetë precizionin, tabela krahason dy përkufizime, jo dy
qasje.

**Vendimi.** Të dyja kalojnë nëpër `scoring.confusion`. Modelet prodhojnë
parashikime **jashtë-fold-it** mbi një ndarje të grupuar sipas depos, pra çdo
mostër parashikohet saktësisht një herë nga një model që nuk e ka parë kurrë
projektin e saj — e njëjta formë që prodhojnë detektorët, dhe kusht që të dyja të
krahasohen mostër për mostër e jo vetëm përmbledhje me përmbledhje.

Pajtimi raportohet me kappa-n e Cohen-it plus të katër qelizat. Dy detektorë që
pothuajse kurrë s'ndezin pajtohen mbi 90% të një bashkësie ku 78% e etiketave janë
`none` pa mësuar asgjë nga njëri-tjetri; pyetja që ka vlerë nuk është sa shpesh
pajtohen A dhe B, por çka kap secila **vetëm**.

**Pasojat.** Kodimi i verdiktit në CSV u centralizua pasi një lexues që hamendësoi
`"True"` kundrejt një shkruesi që nxjerr `"1"` prodhoi një tabelë pajtimi krejt me
zero — dhe një tabelë me zero duket si gjetje, jo si defekt. Tani `decode_verdict`
pranon të dyja drejtshkrimet dhe e ndal ekzekutimin për çdo gjë tjetër.

---

### VD-26: Kalimi i shtrenjtë shkruan atomikisht dhe rifillon

**Konteksti.** Ndërtimi i tabelës së veçorive zgjat ~95 minuta. Një ekzekutim
dështoi te depoja 130 nga 522 me kod dalje 4 dhe pa asnjë përjashtim Python — pra
procesi u vra nga jashtë, jo nga një defekt në kod. Shkaku i saktë mbetet i
paidentifikuar.

Pasoja ishte shumë më e rëndë se humbja e 95 minutave: skripti e hapte skedarin e
komituar me `"w"`, ndaj **e shkatërroi tabelën e mirë** para se të shkruante rreshtin
e parë. Ajo u rikuperua nga git-i, por vetëm sepse ishte e komituar.

**Vendimi.** Dy ndryshime, të dyja të domosdoshme veç e veç.

*Atomik:* rreshtat shkojnë te `mlcq_dataset.csv.part` dhe e zëvendësojnë skedarin
real vetëm pasi ekzekutimi mbaron. Një ekzekutim i dështuar nuk mund ta prekë
artefaktin e komituar.

*I rifillueshëm:* `mlcq_dataset.progress.json` mban depot e përfunduara, numërimet
dhe **listën e kolonave**. Ekzekutimi tjetër i kapërcen depot e bëra. Kontrolli i
kolonave nuk është ceremoni: një skedar i pjesshëm i shkruar me një skemë tjetër nuk
mund të zgjatet, sepse rezultati do të ishte një CSV me dy skema — një skedar që
parsohet dhe gënjen. Mospërputhja e nis nga e para.

Numërimi i progresit vazhdon të llogarisë të gjitha depot, jo vetëm ato që kanë
mbetur, që raportimi të lexohet kundrejt punës së plotë.

**Alternativat.** Rifillim nga zeroja çdo herë: e pranueshme për 2 minuta, jo për 95.
Ruajtje në një bazë të dhënash: shton varësi dhe e humb lexueshmërinë që e bën CSV-në
dëshmi. Shkrim rresht-për-rresht drejt e te skedari real me `"a"`: nuk dallon dot një
ekzekutim të përfunduar nga një të ndërprerë.

**Pasojat.** I verifikuar nga fundi në fund, jo vetëm i shkruar: një ekzekutim mbi 25
depo u vra te depoja 23, u rifillua, dhe prodhoi 269 rreshta — saktësisht sa
ekzekutimi i panderprerë — pa header të dyfishuar dhe pa asnjë `sample_id` të
përsëritur. Ky verifikim është manual; `load_progress` dhe `save_progress` rrinë te
skripti dhe nuk mbulohen nga suita.

---

### VD-27: Motori i refaktorimit riparson skedarin dhe punon mbi bajta

**Konteksti.** Një `Smell` thotë cilën klasë e metodë gjeti dhe në cilin rresht.
Për ta rishkruar, motorit i duhet nyja e pemës — dhe modeli nuk e mban atë: ai
ruan vetëm numra rreshtash, pa offset-e bajtash dhe pa strukturë brenda trupit.

**Vendimi.** Motori e rilexon skedarin nga disku dhe e riparson. Dy arsye, të dyja
të mjaftueshme veç e veç.

*Modeli mund të jetë i vjetruar.* Ai u mat dikur; skedari që do rishkruhet është
ai që ndodhet në disk tani. Rishkrimi mbi offset-e të matura kundrejt një teksti
tjetër është pikërisht mënyra si prishet një skedar.

*Modeli është shumë i trashë.* Guard Clauses kërkon nyjet `if_statement`, blloqet
dhe kufijtë e sakta të tyre. Modeli mban metoda dhe fusha; asgjë nga kjo.

Puna bëhet **mbi bajta, jo karaktere**. tree-sitter jep offset-e bajtash dhe Java-ja
është UTF-8: një skedar me identifikues, koment ose varg jo-ASCII ka më shumë bajta
se karaktere. Prerja sipas indeksit të karakterit e pret një sekuencë shumë-bajtëshe
në mes dhe prodhon një skedar që ose s'dekodohet, ose dekodohet gabim.

Lokalizimi ankorohet te **rreshti** dhe verifikohet me **emrin**, njësoj si përputhja
MLCQ↔entitet (VD-19). E kundërta dështon te mbingarkesat, ku disa nyje ndajnë emrin
dhe vetëm pozicioni i dallon; verifikimi me emër pastaj kap rastin që ka rëndësi —
një skedar i ndryshuar që kur u mat, ku rreshti tani mban diçka krejt tjetër.

**Pasojat.** `parsing/` ekspozon `parse_tree`. Motori mund të refuzojë me
`UNPARSEABLE` ose thjesht të mos e gjejë entitetin, dhe të dyja janë dalje të sakta.

---

### VD-28: Refuzimi është enum i numërueshëm, jo tekst i lirë

**Konteksti.** §4 e kartës thotë se motori refuzon në vend që të prishë, dhe se
refuzimi është rezultat i saktë. Kriteri i daljes së Fazës 3 kërkon **shpërndarjen
e arsyeve të refuzimit** si tabelë në punim.

**Vendimi.** `Refusal` është `StrEnum` me tetë vlera, secila emërton diçka që pema
e analizës nuk e provoi dot. Teksti i lirë nuk agregohet dot në tabelë, dhe një
tabelë është pikërisht ajo që kërkohet.

`Outcome.rewrite()` refuzon të ndërtohet pa editime: «u aplikua» nuk shprehet dot
pa ndryshim real, ndaj numërimi nuk mund të raportojë një ndryshim që s'ndodhi.

**Pasojat.** Bashkësia rritet vetëm kur një transformim ka nevojë për arsye
vërtet të re. Ripërdorimi i një arsyeje afër-përafërt do ta turbullonte pikërisht
tabelën për të cilën ekziston.

---

### VD-29: Kushti negohet duke u mbështjellë, jo duke u përmbysur

**Konteksti.** Guard Clauses e kthen `if (C) { trupi }` në `if (jo-C) return;`
plus trupin. Si prodhohet «jo-C»?

**Vendimi.** `!(C)` mbi tekstin origjinal. Kurrë përmbysje e operatorit.

Rishkrimi i `a > b` në `a <= b` është **i gabuar për numrat me presje**: nëse njëra
anë është NaN, të dyja janë false, ndaj ato nuk janë negativë të njëri-tjetrit.
Dhe përmbysja me dorë e një kushti të përbërë është mënyra si shkruhen defektet
e De Morgan-it.

Mbështjellja është mekanike dhe e saktë për çdo shprehje boolean, përfshirë një me
efekte anësore — ajo vlerësohet saktësisht një herë në të dyja rastet.

**Pasojat.** Dalja është pak më e zhurmshme se ajo që do të shkruante një njeri.
Kjo është këmbim i pranuar: motori garanton ekuivalencë, jo elegancë.

---

### VD-30: Radha e transformimeve përcaktohet nga lokaliteti, jo nga vështirësia

**Konteksti.** Plani i rendiste pesë transformimet sipas «rrezikut të
korrektësisë», duke supozuar se vështirësia dhe rreziku ecin bashkë. Përgatitja e
transformimit të dytë nxori se supozimi është i gabuar, dhe për dy arsye të
pavarura.

**Arsyeja e parë: parser-i me qëllim nuk zgjidh simbole.** Kjo e ndan bashkësinë
në dysh, dhe jo aty ku e ndante vështirësia:

| Transformimi | Çfarë duhet provuar | E provueshme? |
|---|---|---|
| Guard Clauses | vetëm trupi i një metode | po |
| Extract Method | vetëm trupi i një metode | **po** |
| Introduce Parameter Object | çdo pikë thirrjeje | vetëm për metoda `private` |
| Encapsulate Field | çdo referencë ndaj fushës, kudo | jo |
| Move Method | çdo pikë thirrjeje dhe çdo referencë | jo |

Extract Method vlerësohej «e lartë», por e gjithë analiza e saj — variablat hyrëse,
ato dalëse, rrjedha e kontrollit — ndodh brenda një trupi të vetëm metode, dhe pema
e analizës e mbulon plotësisht. Encapsulate Field vlerësohej «mesatare», por kërkon
gjetjen e çdo `x.fusha` në projekt dhe provimin se `x` është i tipit të duhur, çka
kërkon zgjidhës simbolesh që VD-02 e përjashtoi me qëllim.

**Arsyeja e dytë, dhe më e rëndësishmja: Encapsulate Field e përkeqëson Data Class
sipas vetë përkufizimit të strategjisë.** E matur, jo e arsyetuar:

| | WOC | NOPA+NOAM | WMC | DataClass |
|---|---|---|---|---|
| Para (5 fusha publike) | 0.167 | 5 | 1 | **nuk ndez** |
| Pas (Encapsulate Field) | 0.091 | 10 | 11 | **ndez, critical** |

Sepse WOC është pjesa e anëtarëve publikë që *bëjnë diçka*, dhe NOAM numëron
akses-metodat. Encapsulate Field e shndërron një fushë publike në dy akses-metoda
publike: emëruesi i WOC-ut rritet ndërsa numëruesi qëndron, dhe NOPA+NOAM rritet
me një. Të dyja kushtet lëvizin më thellë në erë.

Kjo nuk është defekt i implementimit tonë. Fowler-i e trajton Encapsulate Field si
hap **përgatitor**; ilaçi për një Data Class është Move Method — të sillet sjellja
brenda. Një mjet që aplikon vetëm hapin e parë e përkeqëson matjen që pretendon se
përmirëson.

**Vendimi.** Transformimi i dytë është **Extract Method**, jo Encapsulate Field.

Encapsulate Field nuk automatizohet. Mbetet në `REFACTORINGS` si **propozim**, sepse
si këshillë për një njeri është e saktë, por motori nuk e aplikon: nuk i provon dot
parakushtet, dhe i aplikuar vetëm do të ecte në drejtim të gabuar.

**Alternativat.** Ndërtimi i një zgjidhësi simbolesh: rihap VD-02, shton disa mijëra
rreshta, dhe e zhvendos punimin nga «detektim dhe refaktorim» te «ndërtimi i një
front-endi Java». Aplikimi i Encapsulate Field vetëm brenda skedarit: nuk provon dot
se s'ka referenca jashtë tij, pra shkel rregullin «refuzo, mos prish».

**Pasojat.** Rezultati i mësipërm hyn në Kapitullin 5 si gjetje, jo si problem i
zbutur. Ai tregon diçka reale për strategjitë e Lanza & Marinescu-t: ato e matin
Data Class-in nga sipërfaqja publike, ndaj janë të verbra ndaj dallimit mes një
fushe publike dhe një çifti akses-metodash — dallim që për Fowler-in është pikërisht
hapi i parë i ilaçit. Kjo lidhet me gjetjen te `blob`, ku ML-ja u mbështet te
madhësia dhe jo te kohezioni: në të dyja rastet strategjia mat diçka pak më ndryshe
nga ajo që emërton.

---

### VD-31: Nyjet e tree-sitter krahasohen me `==`, kurrë me `is`

**Konteksti.** Analiza e rrjedhës së të dhënave duhet të pyesë vazhdimisht «a është
kjo nyje e njëjta me atë?» — a është ky identifikues ana e majtë e caktimit, a e ka
kalimi arritur kufirin e bllokut.

**Zbulimi.** Lidhjet Python të tree-sitter-it ndërtojnë një mbështjellës **të ri**
në çdo thirrje aksesori. Dy referenca ndaj së njëjtës nyje nuk janë kurrë i njëjti
objekt, dhe `id()` i tyre ndryshon. `Node.__eq__` krahason pozicionin dhe pemën,
pra është i vetmi krahasim që do të thotë atë që duket.

Kjo u mat, jo u hamendësua:

    child_by_field_name('left') dy here  ->  is: False,  ==: True

**Vendimi.** Një funksion i vetëm `same_node` që përdor `==` dhe trajton `None`,
dhe `span_of` për testet e anëtarësisë. Asnjë `is` dhe asnjë `id()` mes nyjeve.

**Pse ka rëndësi.** Defekti dështon **në heshtje**, jo me gabim. Kontrolli
«a është ky identifikues ana e majtë?» thjesht nuk përputhet kurrë, ndaj analiza e
trajton çdo objektiv caktimi si vlerë që lexohet. Për Extract Method kjo do të
thotë parametra të shpikur për variabla që bllokut nuk i duhen — kod që kompilon,
që duket i arsyeshëm, dhe që është i gabuar.

U kap nga testet e shkruara para se të besohej implementimi: pesë prej tyre
dështuan, dhe të pesë kishin të drejtë. Kjo është arsyeja pse §5 kërkon vlera të
derivuara me dorë e jo golden files — një golden file i gjeneruar nga ky kod do ta
kishte fiksuar defektin si sjellje të pritur.

**Pasojat.** I njëjti kurth vlen për çdo kod të ardhshëm mbi pemën. Motori i
refaktorimit është i vetmi vend ku krahasohen nyje, dhe `same_node` rri aty.

---

### VD-32: Verifikimi bëhet në tri nivele, jo në një

**Konteksti.** Karta kërkon që çdo transformim i aplikuar të verifikohet me
`javac`. Kur u provua mbi korpus doli një pengesë e pritur por e pamatur më parë:
**vetëm 8% e skedarëve kompilojnë të vetëm.** Pjesa tjetër importon fqinjët e vet,
dhe pa classpath-in e projektit `javac` dështon para se të preket asgjë.

Këmbëngulja te një kompilim i pastër do të linte 8% të korpusit të verifikueshëm
dhe s'do të thoshte asgjë për pjesën tjetër.

**Vendimi.** Tri kontrolle, nga më i dobëti te më i forti, secili i raportuar veç:

1. **Parsohet.** tree-sitter jep nyje ERROR ose MISSING për tekst që nuk është Java.
   Kap një rishkrim të deformuar dhe vlen për 100% të skedarëve.
2. **Nuk shton lloj të ri gabimi.** `javac` para dhe pas, me krahasim të mesazheve
   **të dallueshme**.
3. **Kompilon.** Për pakicën që kompilon e vetme, pohimi më i fortë i mundshëm.

**Pse lloje e jo numër.** Numërimi u provua i pari dhe doli tepër i rreptë:
nxjerrja e një blloku, parametri i të cilit është tip i importuar, shton edhe një
`cannot find symbol` për atë tip — thjesht sepse skedari kompilohet pa classpath.
Rishkrimi është i saktë dhe gabimi shtesë është artefakt i izolimit. Kjo u mat mbi
një rast konkret, nuk u hamendësua.

Dobësia e krahasimit sipas llojeve është e kundërta: një gabim i futur që lexohet
si njëri tashmë i pranishëm kalon pa u vënë re. Mes një kontrolli që humb ca prishje
dhe një që mohon punë të saktë, i pari është këmbimi i ndershëm — dhe niveli i tretë
ekziston pikërisht për ta mbuluar. Të dyja janë të dokumentuara me test.

**Pasojat.** Ekzekutimi i parë mbi korpus e justifikoi menjëherë veten: 11 nga 125
rishkrime u shënuan si prishëse. Njëri ishte alarm i rremë i llojit të mësipërm; të
tjerët ishin **defekt i vërtetë** — deklarimet brenda një cikli të mëparshëm
numëroheshin si të dukshme, ndaj një emër si `i` kalonte si parametër edhe pse
blloku e deklaronte vetë, dhe dalja nuk kompilonte.

Ai defekt nuk u kap nga 15 testet e shkruara me dorë. E kapi korpusi. Kjo është
arsyeja pse verifikimi empirik nuk zëvendësohet dot me teste njësie, sado të mira.

---

### VD-33: Çdo kalim i gjatë shkruan me rrjedhë dhe rifillon

**Konteksti.** VD-26 e regjistroi këtë mësim për ndërtimin e tabelës së veçorive
pasi një ekzekutim vdiq te depoja 130 nga 522 dhe shkatërroi artefaktin e
komituar. Mësimi u zbatua atje dhe **nuk u bart** te vlerësimi i refaktorimeve.

Pasoja erdhi menjëherë: ai ekzekutim u vra te skedari 400 nga 4409, pas afro dy
orësh, dhe humbi gjithçka — sepse rreshtat mbaheshin në memorie deri në fund.
Nuk kishte as skedar të pjesshëm për t'u shpëtuar.

**Vendimi.** Rregulli vlen për çdo skript që zgjat më shumë se disa minuta, jo
vetëm për atë ku u mësua:

1. Rezultatet shkruhen **ndërsa prodhohen**, jo në fund.
2. Shkrimi shkon te një skedar i pjesshëm dhe e zëvendëson daljen reale vetëm
   pasi ekzekutimi mbaron.
3. Një skedar progresi mban njësitë e përfunduara, që rifillimi të mos i
   përsërisë. Ai mban edhe listën e kolonave: një skedar i pjesshëm i shkruar me
   skemë tjetër nuk zgjatet dot, sepse rezultati do të ishte një CSV që parsohet
   dhe gënjen.

**Pasojat.** Rifillimi testohet, nuk supozohet. Për këtë skript: një ekzekutim u
ndërpre me dorë te skedari 25, u rifillua, dhe prodhoi 192 rreshta pa kokë të
dyfishuar dhe pa mbeturina.

Shkaku i vetë vrasjeve mbetet i paidentifikuar — kod dalje 4 pa asnjë përjashtim
Python, në të dyja rastet. Mund të jetë gjumi i makinës ose ndërhyrje e OneDrive-it.
Rifillueshmëria e bën atë pyetje të parëndësishme, çka është arsyeja pse ajo
zgjidhet para se të hetohet shkaku.

---

### VD-34: Fshirja e pragjeve mat qëndrueshmërinë, nuk zgjedh pragje

**Konteksti.** Fshirja tregoi se dy pragje janë shumë të ndjeshme. Ulja e pragut
të Long Method-it nga 30 në 15 e ngre MCC-në nga 0.580 në 0.690, dhe relaksimi i
klauzolës `FDP ≤ 5` te Feature Envy e ngre nga 0.271 në 0.411 — duke rritur
njëkohësisht edhe precizionin edhe recall-in.

Tundimi i qartë është t'i adoptohen këto vlera dhe të raportohen numra më të mirë.

**Vendimi.** Nuk adoptohen. Pragjet mbeten ato të botuara, dhe fshirja raportohet
si **analizë ndjeshmërie**, jo si kalibrim.

Arsyeja është e njëjta që e bën ndarjen e grupuar të domosdoshme. Zgjedhja e një
pragu sepse ai jep shifrën më të mirë mbi bashkësinë e vlerësimit është përshtatje
ndaj të dhënave të testimit. Numri që do të raportohej më pas nuk do të ishte më
matje e performancës, por matje e sa mirë u zgjodh ai prag mbi po ato të dhëna —
pikërisht defekti që Di Nucci et al. (2018) e identifikuan te literatura e
mëparshme, dhe që ky punim e shmang me qëllim.

Një prag i ri do të kërkonte kalibrim mbi një bashkësi të ndarë dhe vlerësim mbi
një bashkësi tjetër, të paprekur. Korpusi aktual nuk është ndarë kështu, ndaj
pretendimi nuk bëhet.

**Çfarë raportohet.** Se rezultati për dy erëra varet fort nga pragu dhe për dy të
tjera thuajse aspak. Kjo është e vërtetë e dobishme dhe e mbrojtshme: ajo i thotë
lexuesit sa peshë t'i japë secilës shifër.

Dhe ka edhe një gjetje përmbajtësore. Te Feature Envy, relaksimi i `FDP ≤ FEW`
i përmirëson të dyja anët njëherësh. Kur një kufizim heq pozitivë të vërtetë pa
hequr të rremë, ai nuk po ndan zhurmën nga sinjali — pra ajo klauzolë, të paktën
mbi këtë korpus, nuk e bën punën për të cilën është vendosur.

**Pasojat.** Kapitulli 5 e paraqet fshirjen si matje qëndrueshmërie. Adoptimi i
pragjeve të reja regjistrohet te puna e ardhshme, me kushtin e ndarjes së korpusit.
