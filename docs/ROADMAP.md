# Plani i punës

Çfarë ndërtohet, në çfarë radhe, dhe si e dimë që një fazë mbaroi.
Rregullat se *si* punojmë janë në [`ENGINEERING.md`](ENGINEERING.md); arsyet e vendimeve
janë në [`DECISIONS.md`](DECISIONS.md).

## Gjendja aktuale (verifikuar më 2026-08-26)

| Komponenti | Gjendja | Vërejtje |
|---|---|---|
| Parser Java (tree-sitter) | ✅ i plotë | mbulon record/enum/interface |
| Modeli i entiteteve | ✅ i plotë | `ClassInfo`, `MethodInfo`, `FieldInfo` |
| Metrikat (CK + strategji) | ✅ 17 klasë / 9 metodë | një kalim për klasë; LOC-u i unifikuar (VD-21) |
| Detektorët me rregulla (A) | ✅ 8 smells | me `Condition` dhe ashpërsi të derivuar |
| CLI | ✅ text/json/csv/metrics | pikënisje për eksperimentet |
| Korpusi | ✅ 512/522 depo, 95.4% e mostrave | pas ndjekjes së zhvendosjeve (VD-20) |
| Përputhësi MLCQ↔entitet | ✅ 99.8% e mostrave të disponueshme | `evaluation/matcher.py` |
| Harness vlerësimi (A) | ✅ P/R/F1/MCC + ndjeshmëri | `scripts/evaluate_rules.py` |
| Testet | ✅ 124 kalojnë | vlera të derivuara me dorë |
| Porta e cilësisë | ✅ ruff, mypy strict, CI | `backend/pyproject.toml`, `.github/workflows/ci.yml` |
| ML (B) | ✅ e plotë | 4 modele, ndarje sipas depos, modele të serializuara |
| Motori i refaktorimit (C) | ⬜ bosh | `javasmell/refactor/` — **rreziku më i madh tani** |
| API | ⬜ bosh | `javasmell/api/` |
| Frontend | ⬜ s'ekziston | |
| Punimi | 🟡 skeleti + Kapitulli 1 | `docs/thesis/build_thesis.py` |

Afati: ~12 javë deri te dorëzimi (~nëntor 2026).

## Parimi i renditjes: rreziku i madh i pari

Radha nuk shkon sipas shtresave (backend → frontend). Shkon sipas rrezikut.

Pjesa që mund ta rrëzojë punimin nuk është kodi, është **Kapitulli 5
(Rezultatet)**. Pa të dhëna reale dhe pa një hark vlerësimi që i prodhon numrat,
nuk ka çka të raportohet, sado i mirë të jetë sistemi. Prandaj korpusi dhe
vlerësimi vijnë **para** ML-së, para refaktorimit dhe shumë para frontend-it.
Nëse MLCQ del i papërdorshëm (repo të fshira, commit-e të humbura), duam ta
zbulojmë në javën 1, jo në javën 9.

Frontend-i shkon i parafundit sepse është pjesa me rrezikun më të ulët teknik
dhe më e lehtë për ta shkurtuar nëse ngushtohet koha.

---

## Faza 0: Themeli i cilësisë ✅ e përfunduar (2026-08-25)

- ✅ `ruff` (lint + format) dhe `mypy` **strict** mbi `javasmell/`, të dyja pastër
- ✅ GitHub Actions: lint + format + type-check + teste në çdo push, plus një punë
  e veçantë që verifikon JDK 21 (nevojitet nga Faza 3)
- ✅ `pytest-cov`: mbulimi 81% → **91%**
- ✅ `scripts/` me konventat e eksperimenteve; `data/{raw,corpus,results}/`
- ✅ Konfigurimi i konsoliduar në `backend/pyproject.toml` (`pytest.ini` u hoq)
- ✅ Varësitë e ndara: `requirements.txt` (ekzekutim) vs `requirements-dev.txt`

**Çka nxori porta e cilësisë menjëherë:**

1. **Bug real** në `_cyclomatic_complexity`: `Node.text` te tree-sitter është
   `bytes | None`, dhe `analyze_path` kap vetëm `OSError`/`UnicodeDecodeError`,
   pra një `switch_label` pa tekst do ta rrëzonte tërë analizën e projektit, jo
   vetëm atë skedar. I rregulluar me arsyetimin e dokumentuar.
2. **Element i dyfishtë** `"}"` në bashkësinë e përjashtimit të LOC-ut. Heqja
   është pa efekt, por dyfishimi zbulon një hendek; shih më poshtë.
3. **`cli.py` me 0% mbulim**, ndërsa është pikënisja e eksperimenteve. Tani 97%,
   me kontratën e daljes (header-i CSV, çelësat JSON, kodet e daljes) të fiksuar.
4. Ristrukturim i `main()`: `Wrote <file>` raportohet vetëm pasi skedari mbyllet
   pa gabim, jo në `finally` ku dilte edhe kur shkrimi dështonte.

**E mbyllur më 2026-08-26 (VD-21).** Pyetja e hapur ishte nëse rreshta si `};`
duhet të përjashtoheshin nga LOC-u. Kontrolli nxori diçka më të rëndë: ekzistonin
**dy implementime** të LOC-ut dhe kishin devijuar — `java_parser.loc()` (MLOC)
përjashtonte `{`, `}` dhe `});`, ndërsa `calculator._class_loc()` (CLOC)
përjashtonte vetëm `{` dhe `}`. Tani ka një implementim të vetëm, `effective_loc`,
me rregull të parimtë: një rresht i përbërë vetëm nga ndarësa strukturorë nuk është
pohim. Ndikimi u mat para ndryshimit — 0.32% e rreshtave në një mostër prej 30
depove, dhe **zero** në fikstuarat e testeve, prandaj asnjë vlerë e derivuar me dorë
nuk u prek.

---

## Faza 1: Korpusi dhe harness-i i vlerësimit (javët 1–2) ⚠️ kritike

Pjesa më e nënvlerësuar e projektit. Ka tri nën-probleme, secili real:

**Gjendja:** 1.1–1.4 të përfunduara më 2026-08-26.
Korpusi është shkarkuar i plotë: **512 depo nga 522** dhe **4549 nga 4770 mostra
(95.4%)**. Mbulimi u rrit nga 90.0% pasi u ndoqën zhvendosjet e depove me
verifikim të commit-it (VD-20); 10 depo me 152 mostra mbeten të humbura
përfundimisht dhe hyjnë në punim si kufizim i studimit.

Çka dihet tani me siguri, nga vetë të dhënat e shkarkuara:

| Fakti | Vlera |
|---|---|
| Rishikime / mostra unike | 14 739 / 4 770 |
| Depo / commit-e (një commit për depo) | 522 / 522 |
| Skedarë unikë që përmbajnë mostra | 4 560 |
| Smells të mbuluara | blob, data class, long method, feature envy |
| Shpërndarja e ashpërsisë | none 11 448 · minor 1 787 · major 1 129 · critical 375 |
| **Mospajtim mes rishikuesve** | **25.9%** (dhe 25.6% edhe për "a ka erë fare") |
| Mostra me saktësisht 2 rishikues | 3 511 nga 4 747 |
| Depo të materializuara | 512 nga 522 (98.1%) |
| Mostra me burim në disk | 4 549 nga 4 770 (95.4%) |
| Mostra të lidhura me një entitet | 4 539 nga 4 549 (99.8%) |

Çekuilibri (78% `none`) dhe mospajtimi janë të dy material i detyrueshëm për
Kapitullin 5, jo pengesa për t'u zbutur në heshtje.

**1.1 Marrja e MLCQ** ✅
Dataset-i vjen si CSV nga Zenodo (licencë e hapur) dhe përmban rishikime nga
zhvillues profesionistë për katër smells (Blob, Data Class, Long Method,
Feature Envy) me ashpërsi `none/minor/major/critical`. Çdo rresht tregon
depon GitHub, commit-in dhe entitetin. Kodi *nuk* është brenda dataset-it.

**1.2 Materializimi i korpusit** ✅
Skript që për çdo mostër merr skedarin e duhur në commit-in e duhur dhe e ruan
lokalisht në `data/corpus/`. Kërkesat: cache i pandryshueshëm (shkarko një herë),
punë inkrementale, tolerancë ndaj dështimeve, dhe **raport mbulimi**: sa përqind
e mostrave u zgjidhën dhe sa u humbën sepse depoja s'ekziston më. Ai numër hyn në
punim si kufizim i studimit, nuk fshihet.

**1.3 Përputhja MLCQ ↔ modeli ynë** ✅
Doli më pak i vështirë se sa dukej, por vetëm pasi u mat. `code_name` i MLCQ-së ka
katër formate dhe nuk është i besueshëm; rangu i rreshtave është. I ankoruar te
rreshtat dhe i verifikuar me emrin (VD-19), përputhësi lidh **99.8%** të mostrave
me burim të disponueshëm, dhe mbingarkesat e klasat e brendshme zgjidhen pa asnjë
zgjidhës simbolesh. Raporti prodhohet nga `scripts/report_matching.py` te
`data/results/mlcq_matching.json`, me arsyen e çdo dështimi në CSV-në shoqëruese.

Gjatë kësaj pune doli një defekt që do t'i kishte prishur në heshtje rezultatet:
parser-i nuk i lexonte fare anëtarët e enum-eve, konstantet e interface-ave dhe
komponentët e record-eve (VD-18). Pas rregullimit, mostrat e lidhura u rritën nga
1257 në 1666 mbi të njëjtin korpus.

Mbetet e njohur: 7 mostra janë metoda brenda klasave anonime, të cilat modeli nuk
i mbulon. Veç kësaj, 15 nga 23 depot e paarritshme janë `eclipse/*` që GitHub-u i
ka zhvendosur te organizata të reja, dhe vetëm ato kushtojnë 337 nga 406 mostrat e
humbura. Mbetet vendim i hapur nëse ndjekja e zhvendosjes e ruan vlefshmërinë e së
vërtetës bazë.

**1.4 Vlerësimi i Qasjes A** ✅
`scripts/evaluate_rules.py` prodhon precision, recall, F1, MCC dhe matricën
konfuze për çdo smell, plus dy ndarje që një F1 i vetëm i fsheh: **recall sipas
ashpërsisë** (a i kapim rastet *critical* më mirë se *minor*?) dhe **ndjeshmëria
ndaj agregimit** të mospajtimit mes rishikuesve (mean/max/min/unanimous). Për
`blob` raportohen dy variante sipas VD-22. Rezultatet: `data/results/rules_evaluation.json`
dhe `rules_evaluation_samples.csv`, ky i fundit me një rresht për mostër që çdo
qelizë e tabelës të ndiqet deri te kodi.

Logjika e pikëzimit rri te `evaluation/scoring.py`, jo te skripti, dhe testohet me
matrica të punuara me dorë. Analiza kërkon depon e plotë, jo vetëm skedarët e
mostruar: ATFD, CBO, DIT dhe TCC përcaktohen kundrejt tipave të tjerë (VD-16).

Gjatë kësaj pune doli një defekt i dytë i klasës "një skedar rrëzon gjithçka":
`_iter_type_declarations` ishte rekursiv, dhe një zinxhir prej ~1000 konkatenimesh
— një rresht Java, por 1000 nivele pemë — e kalonte kufirin e rekursionit. Meqë
`analyze_path` kap vetëm `OSError`, ai skedar rrëzonte analizën e çdo depoje pas tij.
Kalimi tani është iterativ, me renditjen e ruajtur dhe të fiksuar me test.

**Rezultatet (4534 mostra të vlerësuara):**

| Erë | Varianti | P | R | F1 | MCC | pozitivë |
|---|---|---|---|---|---|---|
| blob | God Class | 0.814 | 0.100 | 0.178 | 0.232 | 350 |
| blob | + Large Class | 0.720 | 0.257 | 0.379 | 0.340 | 350 |
| data class | strategjia | 0.757 | 0.150 | 0.251 | 0.275 | 186 |
| long method | strategjia | 0.872 | 0.440 | 0.585 | 0.580 | 216 |
| feature envy | strategjia | 0.520 | 0.181 | 0.268 | 0.271 | 72 |

Modeli është i qartë dhe i njëjtë kudo: **precizion i lartë, recall i ulët.** Kur
strategjitë e Lanza & Marinescu ndezin, kanë kryesisht të drejtë (P 0.72–0.87), por
i humbin shumicën e rasteve që rishikuesit i shënojnë. Ky është rezultat për t'u
raportuar, jo për t'u zbutur (`ENGINEERING.md` §3.4).

Por recall-i i përgjithshëm e fsheh gjysmën e historisë. I ndarë sipas ashpërsisë
që caktuan rishikuesit, detektimi **degradon me hijeshi** — i kap rastet e rënda
shumë më mirë se ato të lehtat:

| Erë | Varianti | recall te `major` | recall te `minor` |
|---|---|---|---|
| long method | strategjia | **23/24 (95.8%)** | 72/191 (37.7%) |
| blob | + Large Class | 12/20 (60.0%) | 78/330 (23.6%) |
| blob | God Class | 1/20 (5.0%) | 34/330 (10.3%) |
| feature envy | strategjia | 3/7 (42.9%) | 10/64 (15.6%) |
| data class | strategjia | 6/16 (37.5%) | 22/169 (13.0%) |

Ky është pikërisht dallimi që një F1 i vetëm e bën të padukshëm, dhe arsyeja pse
`recall_by_severity` raportohet gjithmonë. Një mjet që gjen 96% të metodave të gjata
vërtet problematike është i dobishëm edhe kur recall-i i tij i përgjithshëm është 0.44.

VD-22 u vërtetua i dobishëm menjëherë: shtimi i Large Class te `blob` e më se
dyfishon recall-in (0.100 → 0.257) dhe e ngre MCC-në (0.232 → 0.340) me kosto të
matur precizioni (0.814 → 0.720). Pra një pjesë e mirë e asaj që rishikuesit e
quajnë "blob" është thjesht madhësi.

**Parashikimi u verifikua.** Numrat e parë u prodhuan para se të rregullohej prerja
e drejtorive, dhe atëherë u shënua se rigjenerimi pritej t'i lëvizte «në shifrën e
tretë dhjetore, pa ndryshuar asnjë përfundim». Pas rregullimit dhe rindërtimit të
tabelës: 4534 mostra në vend të 4519, dhe e vetmja lëvizje është `long method`
(F1 0.586 → 0.585, MCC 0.581 → 0.580). Të tre erërat e tjera dolën identike.

**Kriteri i daljes:** ✅ numra realë të Qasjes A mbi MLCQ, të riprodhueshëm me një
komandë. Këtu fillon të mbushet Kapitulli 5.

---

## Faza 2: Detektimi me Machine Learning (javët 3–4)

**Gjendja:** makineria e ndërtuar dhe e testuar; pret tabelën e veçorive.

Doli një parakusht që plani nuk e kishte parë: trajnimi kërkon metrikat për secilën
mostër të MLCQ-së, pra pikërisht të njëjtin kalim 95-minutësh mbi korpusin. Po ashtu
edhe fshirja e pragjeve e Fazës 5. Prandaj kalimi u nda nga konsumatorët e tij
(VD-23): `build_dataset.py` e bën një herë dhe shkruan `mlcq_dataset.csv`, i cili
komitohet; `train_models.py` dhe fshirja e lexojnë atë në sekonda.

Rrjedhimisht `evaluate_rules.py` dhe `build_dataset.py` ndajnë një lak të vetëm mbi
korpusin (`evaluation/walk.py`). Nxjerrja u verifikua duke krahasuar daljen para dhe
pas mbi 25 depo: **identike bajt për bajt**.

Ndërtuar dhe testuar:

- `ml/features.py` — tabela → matrica, me rreshtat pa etiketë të hedhur njësoj si te
  `scoring.score`, jo të lexuar si negativë
- `ml/training.py` — katër modelet (VD-24), parashikime jashtë-fold-it mbi
  `GroupKFold` sipas depos (VD-12), permutation importance, kappa e Cohen-it
- `scripts/train_models.py` — eksperimenti, me daljen te `ml_evaluation.json`

Provë mbi 25 depo (numra zhurmë, vetëm për të provuar makinerinë): baseline-i i
shumicës nuk ndez kurrë, siç duhet; dhe veçoritë që modelet zgjodhën janë ato që
përdorin vetë strategjitë — `m_MLOC` e para për long method, `m_LAA` te feature
envy, `c_NOAM` te data class. Nëse kjo qëndron mbi korpusin e plotë, është
nënkapitulli që plani parashikonte.

Gjatë provës doli një defekt që do ta kishte prishur në heshtje tabelën A↔B:
lexuesi krahasonte me `"True"` ndërsa shkruesi nxjerr `"1"`, pra pajtimi dilte zero
kudo — dhe zero duket si gjetje, jo si defekt. Kodimi u centralizua (VD-25).

**Rezultatet (2026-08-26, tabela e plotë: 4534 rreshta, 522 depo):**

| Erë | A: F1 | A: MCC | B: modeli | B: F1 | B: MCC | MCC |
|---|---|---|---|---|---|---|
| blob | 0.178 | 0.232 | gradient boosting | 0.618 | 0.488 | **2.1×** |
| data class | 0.251 | 0.275 | gradient boosting | 0.609 | 0.500 | **1.8×** |
| feature envy | 0.268 | 0.271 | gradient boosting | 0.696 | 0.669 | **2.5×** |
| long method | 0.586 | 0.581 | random forest | 0.756 | 0.713 | **1.2×** |

Baseline-i i shumicës nuk ndez asnjëherë për asnjë erë — recall 0, MCC i
papërcaktuar — pra çdo shifër më sipër është mësim i vërtetë, jo çekuilibër i
shfrytëzuar.

**Ku pajtohen dhe ku jo:**

| Erë | κ | të dy | vetëm A | vetëm B | asnjë |
|---|---|---|---|---|---|
| blob | 0.143 | 39 | 4 | **329** | 1032 |
| data class | 0.227 | 30 | 7 | **144** | 639 |
| feature envy | 0.230 | 12 | 13 | 54 | 742 |
| long method | 0.575 | 105 | 4 | 126 | 1239 |

`vetëm B` tejkalon `vetëm A` kudo, shpesh me një rend madhësie: modeli pothuajse e
përfshin rregullin. Përjashtimi është feature envy, ku rregulli kap 13 raste që
modeli i humb — pjesa relativisht më e madhe, dhe e vetmja ku bashkimi i dy qasjeve
do të kishte kuptim praktik.

**Gjetja që lidh të dy qasjet.** Veçoritë që modelet zgjodhën:

| Erë | Tri kryesoret |
|---|---|
| long method | **m_MLOC**, m_NOAV, m_CC |
| feature envy | m_MLOC, m_NOAV, **m_FDP** (pastaj **m_ATFD**) |
| data class | c_CLOC, **c_WOC**, c_CBO |
| blob | c_CLOC, c_NOF, c_NOAM |

ATFD dhe FDP janë fjalë për fjalë në strategjinë e Feature Envy; WOC është zemra e
Data Class. Pra modelet i rizbuluan disa nga metrikat e Lanza & Marinescu-t pa i
ditur. Por te `blob`, **TCC dhe WMC nuk hyjnë fare në gjashtëshen kryesore** — pikërisht
kushtet e kohezionit dhe të kompleksitetit mbi të cilat është ndërtuar God Class.
Kjo përputhet me VD-22, ku shtimi i Large Class e dyfishoi recall-in: ajo që
rishikuesit e MLCQ-së e quajnë "blob" shpjegohet më mirë me madhësi sesa me kushtin
e kohezionit të strategjisë së botuar. Kjo është një gjetje, jo një dobësi e matjes.

Të dyja qasjet tani vijnë nga i njëjti bazament prej 4534 mostrash, ndaj bashkimi
A↔B punon mbi bashkësinë e plotë (n = 1407/821/823/1483) e jo mbi një prerje.

`evaluate_rules.py --from-dataset` e rirendit detektorët mbi rreshtat e ruajtur në
**0.7 sekonda** në vend të 95 minutave, dhe barazvlefshmëria me matjen e plotë u
verifikua mbi 25 depo: përmbledhja identike, 269 mostra, zero verdikte që ndryshojnë.
Kjo e bën fshirjen e pragjeve të Fazës 5 të mundur fare.

**Kufizim i mbetur.** Rregullimi i prerjes ktheu 15 nga 20 mostrat e humbura; 5
mbeten, 4 prej tyre nën `generated-src/`, ku segmenti nuk është saktësisht `src`,
dhe një nën një drejtori projekti të nivelit të parë të quajtur `build/`. Kjo është
0.09% e rreshtave dhe raportohet si e tillë.

Faza 2 është e mbyllur: modelet e serializuara me manifest, dhe `evaluate_rules.py`
lexon tabelën.

- **Baseline i detyrueshëm**: klasifikues shumicë + regresion logjistik. Pa këtë,
  një F1 prej 0.85 nuk do të thotë asgjë; mund ta japë edhe hamendja.
- **Modelet**: Random Forest dhe Gradient Boosting (scikit-learn). Pa rrjeta
  neurale: dataset-i është i vogël, veçoritë tabelare, dhe interpretueshmëria
  vlen më shumë se një pikë F1.
- **Ndarja**: `GroupKFold` sipas depos. Ndarja e rastësishme sipas rreshtave është
  gabimi klasik dhe fryn rezultatet; shih `ENGINEERING.md` §3.3.
- **Çekuilibri i klasave**: `class_weight`, jo mbi-mostrim naiv. Asnjë ribalancim
  mbi bashkësinë e testimit.
- **Interpretimi**: rëndësia e veçorive me permutation importance. A janë metrikat
  që ML-ja i zgjodhi po ato që përdorin strategjitë e Lanza & Marinescu? Kjo pyetje
  e vetme vlen një nënkapitull të tërë.
- **Krahasimi A vs B**: pajtimi (Cohen's κ), ku njëra kap atë që tjetra humb, dhe a
  ndihmon bashkimi i të dyjave.

**Kriteri i daljes:** model i serializuar, raport vlerësimi i riprodhueshëm, dhe
tabela e krahasimit A vs B.

---

## Faza 3: Motori i refaktorimit (javët 5–7), pjesa më e madhe

Rendi është sipas rrezikut të korrektësisë, nga më e sigurta te më e vështira.

**3.0 Infrastruktura** ✅
`refactor/edits.py` aplikon disa editime mbi rangje bajtash, nga fundi para që
offset-et të mbeten të vlefshme, dhe **refuzon çdo palë që mbivendoset** — dy
editime mbi të njëjtat bajta s'kanë rezultat të përcaktuar, dhe zgjedhja e njërit
do të thoshte se motori hedh ndonjëherë një ndryshim që e raportoi si të aplikuar.
Puna bëhet mbi bajta, jo karaktere (VD-27). Njësia e indentimit maset nga skedari,
ndaj një projekt me tab-e del me tab-e.

`refactor/base.py` mban `Outcome`, `Refusal` dhe `Tally`. Refuzimi është enum i
numërueshëm (VD-28), dhe `Outcome.rewrite()` s'ndërtohet dot pa editime — pra
«u aplikua» nuk shprehet dot pa ndryshim real.

`refactor/locate.py` gjen entitetin në një pemë të riparsuar, i ankoruar te rreshti
dhe i verifikuar me emrin, që mbingarkesat të dallohen dhe një skedar i ndryshuar
që kur u mat të mos rishkruhet gabim.

**3.1 Korniza e parakushteve**
Çdo transformim deklaron çka duhet të jetë e vërtetë. Nëse s'provohet nga pema e
analizës (emër i pazgjidhur, efekt anësor i mundshëm, mbingarkesë e paqartë),
transformimi kthen "e paaplikueshme" me arsye. **Refuzimi është rezultat i saktë**
dhe raportohet si i tillë.

**3.2 Transformimet**

Radha u rishikua pasi u ndërtua transformimi i parë: kufizimi real nuk është
vështirësia, është **lokaliteti** (VD-30). Parser-i me qëllim nuk zgjidh simbole,
ndaj çdo transformim që duhet të gjejë pikat e thirrjes ose referencat në projekt
nuk i provon dot parakushtet e veta.

| # | Transformimi | Smell | Çfarë duhet provuar | Gjendja |
|---|---|---|---|---|
| 1 ✅ | Guard Clauses | DeepNesting | një trup metode | e mbaruar |
| 2 | Extract Method | LongMethod, BrainMethod | një trup metode | **në radhë** |
| 3 | Introduce Parameter Object | LongParameterList | çdo pikë thirrjeje | vetëm metoda `private` |
| 4 | Encapsulate Field | DataClass | çdo referencë ndaj fushës | vetëm propozim |
| 5 | Move Method | FeatureEnvy | thirrjet dhe referencat | vetëm propozim |

**Encapsulate Field nuk automatizohet, dhe arsyeja është gjetje më vete.** E matur
mbi një klasë me pesë fusha publike: para saj WOC=0.167 dhe NOPA+NOAM=5, pra
detektori **nuk ndez**; pas saj WOC=0.091 dhe NOPA+NOAM=10, pra ndez si **critical**.
Refaktorimi që mjeti e rekomandon për Data Class e çon klasën më thellë në erë sipas
vetë përkufizimit të strategjisë, sepse ai shndërron një fushë publike në dy
akses-metoda publike dhe të dyja kushtet e strategjisë e numërojnë këtë si përkeqësim.

Kjo nuk është defekt i yni: Fowler-i e trajton Encapsulate Field si hap përgatitor,
dhe ilaçi i vërtetë është Move Method. Por një mjet që aplikon vetëm hapin e parë
ecën në drejtim të gabuar, ndaj motori e propozon dhe nuk e aplikon.

**Transformimi i parë është i mbaruar.** `guard_clauses.py` e rishkruan saktësisht
formën ku i tërë trupi i një metode `void` është mbështjellë në një kusht të vetëm
pa `else`, dhe refuzon gjithçka tjetër me arsye: metodë jo-`void` (garda do të
kërkonte një vlerë kthimi që s'shpikim dot), degë `else`, trup me më shumë se
kushtin, degë boshe, degë pa bllok, metodë abstrakte. Kushti negohet duke u
mbështjellë me `!(...)`, kurrë duke u përmbysur — `a > b` → `a <= b` është i gabuar
kur njëra anë është NaN (VD-29).

Dymbëdhjetë teste, përfshirë njërin që e kompilon daljen me `javac`.

Për **Extract Method**, kufizim i qëllimshëm: vetëm blloqe me së shumti një
variabël dalëse, pa `return`/`break`/`continue` që dalin jashtë bllokut. Një motor
që refuzon shumë por nuk gabon kurrë është shkencërisht i mbrojtshëm; një që
provon gjithçka dhe prish kodin nuk është.

Për **Move Method**, vendim i planifikuar: ndoshta vetëm propozim me klasën e
synuar, pa aplikim automatik. Vendoset kur të arrijmë aty, dhe regjistrohet.

**3.3 Verifikimi**
`javac` mbi projektin pas çdo transformimi. Për projektet e korpusit me suitë
testesh, testet para dhe pas. Pretendimi empirik i punimit është: *nga N raste të
detektuara, M u transformuan automatikisht, të gjitha kompiluan, dhe K ruajtën
sjelljen sipas testeve të vetë projektit*.

**Kriteri i daljes:** tabela N/M/K mbi një korpus të deklaruar, plus shpërndarja e
arsyeve të refuzimit.

---

## Faza 4: API dhe ndërfaqja web (javët 8–9)

**Backend (FastAPI):** `POST /analyze`, `GET /projects/{id}/smells`,
`GET /projects/{id}/metrics`, `POST /refactor/preview` (kthen diff, nuk shkruan).
Validim me Pydantic, kufij burimesh, gabime të strukturuara. Kërcënimet reale janë
në `ENGINEERING.md` §6.

**Frontend (React + TypeScript + Vite):**
- Përmbledhje projekti: numra, shpërndarje sipas ashpërsisë, klasat më problematike
- Lista e smells me filtra sipas llojit/ashpërsisë/skedarit
- Detaji: kodi me theksim, kushtet e plotësuara me vlerat e matura, metrikat
- Krahasimi A vs B për të njëjtin entitet
- Pamja e diff-it para/pas për refaktorimin

Çdo pamje me katër gjendje: loading, sukses, bosh, gabim. Pa "happy path" të vetëm.

**Kriteri i daljes:** rrjedhë e plotë nga zgjedhja e projektit te diff-i i propozuar.

---

## Faza 5: Eksperimentet finale dhe shkrimi (javët 10–11)

- **Analiza e ndjeshmërisë**: fshirje e pragjeve rreth vlerave të Lanza & Marinescu,
  për të treguar sa e qëndrueshme është detektimi. Pikërisht për këtë pragjet
  qëndrojnë të centralizuara në `thresholds.py`.
- Kapitulli 2 (Literatura), 3 (Problemi), 4 (Metodologjia, nga `DECISIONS.md`),
  5 (Rezultatet, nga `data/results/`).
- Figurat dhe tabelat gjenerohen nga skriptet, jo me kopjim manual. Nëse një numër
  ndryshon, rigjenerohet gjithçka.

---

## Faza 6: Finalizimi (java 12)

Kapitulli 6, abstrakti, referencat, verifikimi i formatimit UBT, prezantimi.
Kjo javë është edhe rezervë; historikisht diçka rrëshqet.

---

## Rreziqet kryesore

| Rreziku | Ndikimi | Zbutja |
|---|---|---|
| Depot e MLCQ të fshira/commit-e të humbura | mostra të pamjaftueshme | Faza 1 në javën e parë; snapshot lokal i menjëhershëm; raportim i mbulimit si kufizim |
| Përputhja MLCQ↔entitet del e pasaktë | vlerësim i pavlefshëm | teste të dedikuara për matcher-in; verifikim manual i një kampioni |
| Extract Method prish kodin | pretendim i rrëzuar | parakushte konservative + verifikim me `javac`; refuzimi lejohet |
| Faza 3 zgjatet përtej javës 7 | ngushtohet koha e shkrimit | Move Method dhe Extract Method bien në "vetëm propozim"; punimi qëndron |
| Frontend-i konsumon kohën e shkrimit | kapituj të dobët | frontend-i mbahet minimal; CLI-ja i mbulon eksperimentet |
| Rezultate ML të dobëta | ankth i panevojshëm | rezultati negativ është rezultat; raportohet dhe diskutohet |

## Jashtë fushëveprimit

I regjistrojmë që të mos rihapen: gjuhë të tjera veç Java-s, plugin IDE, integrim
CI/CD për përdorues të tjerë, refaktorim me LLM, analizë ndër-projektesh në shkallë
të madhe, dhe çdo veçori shumë-përdoruesish.
