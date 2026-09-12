# Code Smell Detection and Refactoring Recommendations

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

Të tria qasjet janë të vlerësuara mbi **4 534 mostra nga 522 depo Java**, me të vërtetën
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
  evaluation/  Përputhja me MLCQ-në dhe harness-i i vlerësimit
  api/         FastAPI
backend/tests/ Teste me vlera të derivuara me dorë
frontend/      React + TypeScript
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

Ndërfaqja, me dy procese:

```bash
JAVASMELL_ROOT=/shtegu/i/lejuar python -m uvicorn javasmell.api.app:create_app --factory --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

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
| 15 | `build_figures.py` | figurat e Kapitullit 5 | sekonda |
| 16 | `review_rewrites.py --sample` | mostra e rishkrimeve dhe fleta e vlerësimit | sekonda |
| 17 | `review_rewrites.py --score` | cilësia e rishkrimeve sipas rishikuesit | sekonda |
| 18 | `fetch_pmd.py` | mjeti i jashtëm i krahasimit, jashtë git-it | minuta, një herë |
| 19 | `compare_with_pmd.py` | krahasimi me PMD-në mbi të njëjtat mostra | orë |
| 20 | `blocking_conditions.py` | cila klauzolë e ndal secilën strategji | sekonda |
| 21 | `blob_recall.py` | çfarë mbetet pa u kapur te Blob-i | sekonda |

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
