# Code Smell Detection and Refactoring Recommendations

## English summary

Bachelor thesis in Computer Science and Engineering at UBT, academic year 2025/2026.
Author: Florent Latifi. Supervisor: Altina Salihu. The rest of this README, the
thesis and the decision log are in Albanian.

The system analyses **Java** projects, detects *code smells* with three independent
approaches, and proposes refactorings that are verified before they are offered.

| Approach | How it works |
|---|---|
| A. Rules and metrics | Detection strategies from Lanza & Marinescu (2006), thresholds from the literature |
| B. Machine learning | Random forest and gradient boosting over the metric vector, labelled with the MLCQ dataset |
| C. Refactoring engine | Deterministic AST transformations from Fowler's catalogue, each verified with `javac` |

Everything runs locally on open-source tools; no paid service is involved.

**Results.** All three approaches are evaluated on 4,534 samples from 512 Java
repositories, with ground truth from professional reviewers (MLCQ). Splits are grouped
by repository, never random by row, and the majority-class baseline never fires, so
every score below is real learning rather than exploited class imbalance.

| Smell | A: MCC | B: MCC | Best model |
|---|---|---|---|
| Long Method | 0.580 | **0.713** | random forest |
| Feature Envy | 0.271 | **0.669** | gradient boosting |
| Data Class | 0.275 | **0.500** | gradient boosting |
| Blob | 0.232 | **0.488** | gradient boosting |

The refactoring engine applies Guard Clauses, Extract Method and Introduce Parameter
Object (for `private` methods). It proposes two more without applying them, because
they need every reference in the project, which the analysis cannot prove. A refusal
is a correct result and is reported as one.

**Usage.** From `backend/`, the tool prints findings, or writes the safe rewrites as a
unified diff that you review before applying:

```bash
python -m javasmell path/to/project --format patch --out fixes.patch
git apply --check fixes.patch
```

As a build gate, `--fail-on major` exits with code 3 when a finding at or above that
severity remains.

**Stack.** Python 3.13, tree-sitter, scikit-learn, FastAPI, React and TypeScript.
CI runs ruff, mypy (strict) and pytest on every push, and dependencies are pinned so
the published numbers can be reproduced.

---

Punim diplome Bachelor, Shkenca Kompjuterike dhe Inxhinieri, UBT.
Autor: Florent Latifi · Mentore: Altina Salihu · Viti akademik 2025/2026 · Dorëzimi: 2026

Sistem që analizon projekte **Java**, detekton *code smells* me tri qasje të pavarura
dhe gjeneron rekomandime refaktorimi të verifikueshme.

## Qasjet e detektimit

| # | Qasja | Përshkrimi |
|---|---|---|
| A | Rregulla dhe metrika | Strategji detektimi nga Lanza & Marinescu (2006), me pragje nga literatura |
| B | Machine Learning | Klasifikues i trajnuar mbi vektorin e metrikave, i etiketuar me dataset-in MLCQ |
| C | Motor refaktorimi | Transformime deterministike mbi AST sipas katalogut të Fowler-it, të verifikuara me `javac` |

Sistemi nuk varet nga asnjë shërbim me pagesë: i tërë vargu i mjeteve është open-source
dhe analiza ekzekutohet lokalisht.

## Gjendja

Të tria qasjet janë të vlerësuara mbi **4 534 mostra nga 512 depo Java**, me të vërtetën
bazë nga rishikues profesionistë (MLCQ). Numrat rigjenerohen me një komandë.

| Erë | A: MCC | B: MCC | Modeli më i mirë |
|---|---|---|---|
| Long Method | 0.580 | **0.713** | random forest |
| Feature Envy | 0.271 | **0.669** | gradient boosting |
| Data Class | 0.275 | **0.500** | gradient boosting |
| Blob | 0.232 | **0.488** | gradient boosting |

Modeli i shumicës nuk ndez asnjëherë për asnjë erë, ndaj çdo shifër më sipër është
mësim i vërtetë dhe jo çekuilibër i shfrytëzuar. Ndarja është e grupuar sipas depos,
kurrë e rastësishme sipas rreshtave.

Motori i refaktorimit aplikon tri transformime — Guard Clauses, Extract Method dhe
Introduce Parameter Object për metodat `private` — dhe i propozon dy të tjerat pa i
aplikuar, sepse ato kërkojnë gjetjen e çdo reference në projekt, çka analiza nuk e
provon dot. **Refuzimi është rezultat i saktë** dhe raportohet
si i tillë.

## Struktura

```
backend/javasmell/
  model/       Modeli i entiteteve (ClassInfo, MethodInfo, FieldInfo)
  parsing/     Front-end Java mbi tree-sitter
  metrics/     Suita CK + metrikat e strategjive të detektimit
  detectors/   Detektorët me rregulla
  ml/          Trajnimi dhe inferenca e modelit
  refactor/    Motori i transformimeve mbi AST
  projects/    Importi i një depoje publike nga GitHub
  evaluation/  Përputhja me MLCQ-në dhe harness-i i vlerësimit
  api/         FastAPI
backend/tests/ Teste me vlera të derivuara me dorë
frontend/      React + TypeScript
tools/         Nisësi për Windows
docs/thesis/   Punimi sipas shabllonit të UBT-së
```

## Metrikat e implementuara

**Klasë:** CLOC, NOM, NOF, WMC, AMW, MAXCC, TCC, LCOM, LCOM3, ATFD, CBO, RFC, WOC, NOPA, NOAM, DIT, NOC
**Metodë:** MLOC, CC, NP, MAXNESTING, ATFD, FDP, LAA, NOAV, CINT

## Përdorimi nga rreshti i komandës

```bash
python -m javasmell path/to/project
```

Rishkrimet që motori i konsideron të sigurta dalin si patch i unifikuar. Asgjë
nuk shkruhet mbi kodin: diff-i lexohet i pari, dhe aplikimi mbetet vendim i
autorit (VD-49).

```bash
python -m javasmell path/to/project --format patch --out fixes.patch
```

```bash
git apply --check fixes.patch
```

Numri i ndryshimeve, i vendeve të refuzuara dhe i atyre të shtyra shkon te
stderr, që stdout të mbetet vetëm patch dhe të mund të tubohet drejt e te
`git apply`. Një vend i shtyrë ofrohet sërish në ekzekutimin pasardhës. Refuzimet
grupohen sipas arsyes, me një shembull për secilën (VD-90).

Si portë ndërtimi, komanda del me kod 3 kur mbetet një gjetje në ashpërsinë e
kërkuar ose mbi të. Kodet 1 dhe 2 do të thonë se vetë mjeti nuk punoi, ndaj një
portë i dallon dot të dyja pa lexuar asnjë rresht dalje (VD-92).

```bash
python -m javasmell path/to/project --fail-on major
```

Pragjet e publikuara janë të parazgjedhura. Për t'i lëvizur pa e prekur kodin, një
skedar TOML emërton vetëm ato që ndryshojnë, me emrat e Shtojcës 8.2 të punimit;
të tjerat mbeten si janë. Komanda i shkruan te stderr pragjet e ndryshuara, që një
raport i tillë të mos ngatërrohet me një të matur me vlerat e publikuara. Një emër
i panjohur, një vlerë jo-numerike ose një vlerë zero a negative e ndalin komandën
me kod 2, para analizës (VD-131).

```toml
# pragje.toml
long_method_loc = 40
feature_envy_laa = 0.5
```

```bash
python -m javasmell path/to/project --thresholds pragje.toml
```

I njëjti patch shërbehet nga `POST /refactor/patch` dhe nga ndërfaqja, nën
`JAVASMELL_TIMEOUT_S`: verifikimi ekzekuton `javac` për çdo skedar të rishkruar,
ndaj koha kufizohet dhe një buxhet i mbaruar jep patch më të shkurtër me numrin e
skedarëve të paarritur, jo kërkesë të dështuar (VD-50).

## Zhvillimi

Përgatitja e mjedisit:

```bash
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Katër kontrollet që ekzekuton edhe CI-ja, nga dosja `backend/`:

```bash
ruff check . && ruff format --check . && mypy && pytest -q --cov
```

**Përdorimi.** Ndërfaqja ndërtohet një herë, dhe pastaj një proces i vetëm i
shërben të dyja: faqen te `/` dhe API-në te `/api` (VD-127).

```bash
cd frontend && npm install && npm run build
```

```bash
cd backend && JAVASMELL_ROOT=/shtegu/i/lejuar python -m uvicorn javasmell.api.bundle:create_bundle --factory --port 8000
```

Mjeti hapet te `http://localhost:8000`. Në Windows, e njëjta gjë bëhet me dy
klikime mbi `Nis-JavaSmell.bat`: ai hap dialogun e sistemit për të zgjedhur
dosjen e lejuar, e ndërton ndërfaqen vetëm nëse kodi i saj ka ndryshuar, nis
procesin, pret derisa përgjigjet dhe hap shfletuesin. Dosja e zgjedhur mbahet
mend, dhe porti kontrollohet para nisjes, që një server i vjetër me rrënjë tjetër
të mos analizojë në heshtje dosjen e gabuar (VD-126).

Brenda ndërfaqes, projekti zgjidhet me butonin **Zgjidh**: dosjet shfletohen
brenda rrënjëve të lejuara, dhe ato që mbajnë kod Java shënohen. Skeda **Nga
GitHub** importon një depo publike nga një lidhje — shkarkohen vetëm skedarët
`.java`, te `data/projects/`, që është rrënja e dytë e lexueshme.

**Zhvillimi i ndërfaqes**, me dy procese dhe rifreskim të menjëhershëm:

```bash
JAVASMELL_ROOT=/shtegu/i/lejuar python -m uvicorn javasmell.api.app:create_app --factory --port 8000
```

```bash
cd frontend && npm run dev
```

**Siguria.** Mjeti është për një përdorues, në makinën e vet, dhe lidhet vetëm
te `127.0.0.1`; autentikimi është qëllimisht jashtë fushës (`docs/ENGINEERING.md`
§6). Kjo nuk mjafton vetë, sepse faqet e tjera që hap përdoruesi mund ta arrijnë
localhost-in përmes shfletuesit të tij, ndaj çdo kërkesë kalon një roje (VD-127):

- vetëm emrat `localhost`, `127.0.0.1` dhe `::1` te koka `Host` (kundër DNS rebinding);
- asnjë POST nga një origjinë e huaj (kundër kërkesave ndër-faqe);
- `X-Frame-Options` dhe `frame-ancestors 'none'` (kundër mbështjelljes në iframe);
- shtigjet mbyllen brenda rrënjëve të lejuara, dhe `/source` lexon vetëm skedarë `.java`;
- importi shkruan vetëm `.java`, me kufij për arkivin, për skedarin dhe për totalin.

Ekspozimi i shërbimit në rrjet nuk mbështetet: ai do të kërkonte autentikim, izolim
të proceseve dhe një model tjetër kërcënimesh.

Qasja B shërbehet vetëm nëse modelet janë trajnuar — `data/models/` nuk komitohet,
sepse depoja mban recetën dhe jo rezultatin:

```bash
python scripts/train_models.py
```

Pa to, `/analyze` me `include_model` kthen `available: false` me arsyen, dhe
rregullat përgjigjen si zakonisht. Modeli pyetet vetëm mbi një dosje projekti, jo
mbi një skedar të vetëm (VD-48).

Konfigurimi i të gjitha mjeteve është i përqendruar në `backend/pyproject.toml`.
`mypy` punon në modalitet **strict**, dhe paralajmërimet e testeve trajtohen si
gabime: një `DeprecationWarning` nga tree-sitter është pikërisht sinjali që
kalon pa u vënë re derisa një përditësim e prish parser-in.

## Dokumentimi i procesit

| Skedari | Roli |
|---|---|
| [`docs/ENGINEERING.md`](docs/ENGINEERING.md) | Si punojmë: arkitektura, invariantet, kriteret e përfundimit |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Çka ndërtohet dhe në çfarë radhe, me rreziqet |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Pse: regjistri i vendimeve, lëndë e parë për Kapitullin 4 |

## Riprodhimi i rezultateve

Skriptet ekzekutohen në këtë radhë; koha është për një laptop pa GPU.

| # | Skripti | Prodhon | Kohë |
|---|---|---|---|
| 1 | `fetch_corpus.py` | korpusi, jashtë git-it | orë, një herë |
| 2 | `report_matching.py` | mbulimi i përputhjes MLCQ↔entitet | ~2 min |
| 3 | `build_dataset.py` | tabela e veçorive, e komituar | ~56 min |
| 4 | `evaluate_rules.py --from-dataset data/results/mlcq_dataset.csv` | numrat e Qasjes A | sekonda |
| 5 | `train_models.py` | numrat e Qasjes B dhe modelet | ~3 min |
| 6 | `sweep_thresholds.py` | analiza e ndjeshmërisë | sekonda |
| 7 | `evaluate_refactorings.py` | tabela N/M/K e Qasjes C | orë |
| 8 | `calibrate_thresholds.py` | pragjet e kalibruara jashtë fold-it | sekonda |
| 9 | `reviewer_agreement.py` | tavani i pajtimit mes rishikuesve | sekonda |
| 10 | `bootstrap_intervals.py` | intervalet e besimit | nën një minutë |
| 11 | `refusals_by_severity.py` | refuzimet sipas erës dhe ashpërsisë | ~2 min |
| 12 | `verify_with_project.py` | verdikti brenda kontekstit të projektit | orë |
| 13 | `model_without_project.py` | Qasja B pa kontekstin e projektit | ~2 min |
| 14 | `export_system_reference.py` | tabelat e kësaj shtojce | sekonda |
| 15 | `build_figures.py` | figurat e Kapitujve 4 dhe 5 | sekonda |
| 16 | `review_rewrites.py --sample` | mostra e rishkrimeve dhe fleta e vlerësimit | sekonda |
| 17 | `review_rewrites.py --score` | cilësia e rishkrimeve sipas rishikuesit | sekonda |
| 18 | `fetch_pmd.py` | mjeti i jashtëm i krahasimit, jashtë git-it | minuta, një herë |
| 19 | `compare_with_pmd.py` | krahasimi me PMD-në mbi të njëjtat mostra | orë |
| 20 | `blocking_conditions.py` | cila klauzolë e ndal secilën strategji | sekonda |
| 21 | `blob_recall.py` | çfarë mbetet pa u kapur te Blob-i | sekonda |
| 22 | `train_strategy_features.py` | Qasja B vetëm me metrikat e strategjisë | sekonda |

Hapi 3 është kalimi i shtrenjtë që duhet paguar një herë: ai mat çdo entitet, dhe
hapat 4 deri 6 lexojnë rreshtat e tij. Meqë tabela komitohet, një anëtar komisioni me
një checkout të pastër i riprodhon numrat pa korpusin 4.4 GB.

Hapat 7 dhe 12 shkruajnë në mënyrë inkrementale dhe rifillojnë aty ku mbetën.

Kjo tabelë nuk mirëmbahet me dorë: `docs/thesis/check_reproduction.py` e krahason me
atë të Shtojcës 8.5 dhe e rrëzon ndërtimin nëse ndahen. Ajo ndarje kishte ndodhur —
README-ja mbeti me njëmbëdhjetë hapa, një rresht të dyfishtë, dhe një komandë që nuk
ekzekutohej — dhe pikërisht ajo e shtoi kontrollin.

## Referencat metodologjike

- Chidamber, S. R., Kemerer, C. F. (1994). *A Metrics Suite for Object Oriented Design.*
- Lanza, M., Marinescu, R. (2006). *Object-Oriented Metrics in Practice.*
- Fowler, M. (2018). *Refactoring: Improving the Design of Existing Code*, 2nd ed.
- Madeyski, L., Lewowski, T. (2020). *MLCQ: Industry-relevant code smell data set.*

## Licenca

Kodi publikohet nën licencën MIT: lejohet përdorimi, ndryshimi dhe shpërndarja,
me kusht që njoftimi i të drejtës së autorit të mbetet. Teksti i plotë është te
[`LICENSE`](LICENSE).

Licenca mbulon kodin e këtij depoje. Dataset-i MLCQ, depot Java të korpusit dhe
depot e importuara nga ndërfaqja mbeten nën licencat e veta, dhe asnjëra prej tyre
nuk shpërndahet bashkë me këtë kod.
