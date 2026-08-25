# Plani i punës

Çfarë ndërtohet, në çfarë radhe, dhe si e dimë që një fazë mbaroi.
Rregullat se *si* punojmë janë në [`ENGINEERING.md`](ENGINEERING.md); arsyet e vendimeve
janë në [`DECISIONS.md`](DECISIONS.md).

## Gjendja aktuale (verifikuar më 2026-08-25)

| Komponenti | Gjendja | Vërejtje |
|---|---|---|
| Parser Java (tree-sitter) | ✅ i plotë | 413 rreshta, mbulon record/enum/interface |
| Modeli i entiteteve | ✅ i plotë | `ClassInfo`, `MethodInfo`, `FieldInfo` |
| Metrikat (CK + strategji) | ✅ 17 klasë / 9 metodë | një kalim për klasë |
| Detektorët me rregulla (A) | ✅ 8 smells | me `Condition` dhe ashpërsi të derivuar |
| CLI | ✅ text/json/csv/metrics | pikënisje për eksperimentet |
| Përputhësi MLCQ↔entitet | ✅ 99.8% e mostrave të disponueshme | `evaluation/matcher.py` |
| Testet | ✅ 89 kalojnë, mbulim 92% | vlera të derivuara me dorë |
| Porta e cilësisë | ✅ ruff, mypy strict, CI | `backend/pyproject.toml`, `.github/workflows/ci.yml` |
| ML (B) | ⬜ bosh | `javasmell/ml/` |
| Motori i refaktorimit (C) | ⬜ bosh | `javasmell/refactor/` |
| API | ⬜ bosh | `javasmell/api/` |
| Frontend | ⬜ s'ekziston | |
| Harness vlerësimi | ⬜ s'ekziston | **rreziku më i madh** |
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

**Mbetet e hapur (vendim i autorit):** bashkësia `{"{", "}", "});"}` që përjashton
rreshtat pa logjikë nga LOC-u nuk përmban `"};"`: mbyllja e një klase anonime
ose e një inicializuesi vargu. Përfshirja do të ishte në përputhje me qëllimin e
deklaruar të metrikës, por **ndryshon vlerat e matura** të MLOC/CLOC dhe rrjedhimisht
detektimet e Long Method dhe Large Class. Nuk e preka njëanshmërisht (shih
`ENGINEERING.md` §3.2). Momenti i duhur për ta vendosur është **para** Fazës 1, sepse
pas saj ndryshon çdo numër i publikuar.

---

## Faza 1: Korpusi dhe harness-i i vlerësimit (javët 1–2) ⚠️ kritike

Pjesa më e nënvlerësuar e projektit. Ka tri nën-probleme, secili real:

**Gjendja:** 1.1, 1.2 dhe 1.3 të përfunduara më 2026-08-25; 1.4 në radhë.
Korpusi është shkarkuar i plotë: 499 depo nga 522 dhe 4295 nga 4770 mostra (90.0%),
4.4 GB dhe 689 233 skedarë `.java`. Të 23 depot e mbetura kthejnë HTTP 404.

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
| Depo të materializuara | 499 nga 522 (95.6%) |
| Mostra me burim në disk | 4 295 nga 4 770 (90.0%) |
| Mostra të lidhura me një entitet | 4 286 nga 4 295 (99.8%) |

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

**1.4 Vlerësimi i Qasjes A** ⬜ hapi tjetër
`scripts/evaluate_rules.py` → precision, recall, F1 dhe MCC për çdo smell, matricë
konfuze, dhe ndarje sipas ashpërsisë (a i kapim rastet *critical* më mirë se
*minor*?). Rezultatet në `data/results/`.

**Kriteri i daljes:** numra realë të Qasjes A mbi MLCQ, të riprodhueshëm me një
komandë. Këtu fillon të mbushet Kapitulli 5.

---

## Faza 2: Detektimi me Machine Learning (javët 3–4)

Vektori i veçorive ekziston tashmë: `python -m javasmell <path> --format metrics`.

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

**3.0 Infrastruktura**
Rishkrim mbi rangjet e bajtave që i jep tree-sitter: aplikim i disa editimeve në
një skedar pa kolizion, ruajtje e indentimit, dhe një `RefactoringResult` që mban
edhe rastet e refuzuara me arsyen përkatëse.

**3.1 Korniza e parakushteve**
Çdo transformim deklaron çka duhet të jetë e vërtetë. Nëse s'provohet nga pema e
analizës (emër i pazgjidhur, efekt anësor i mundshëm, mbingarkesë e paqartë),
transformimi kthen "e paaplikueshme" me arsye. **Refuzimi është rezultat i saktë**
dhe raportohet si i tillë.

**3.2 Transformimet**

| # | Transformimi | Smell | Vështirësia |
|---|---|---|---|
| 1 | Replace Nested Conditional with Guard Clauses | DeepNesting | e ulët |
| 2 | Encapsulate Field | DataClass | mesatare, kërkon rishkrim referencash |
| 3 | Introduce Parameter Object | LongParameterList | mesatare |
| 4 | Extract Method | LongMethod, BrainMethod | e lartë, analizë hyrje/dalje |
| 5 | Move Method | FeatureEnvy | shumë e lartë |

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
