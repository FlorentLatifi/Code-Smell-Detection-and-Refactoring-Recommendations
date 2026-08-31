# Code Smell Detection and Refactoring Recommendations

Punim diplome Bachelor, Shkenca Kompjuterike dhe Inxhinieri, UBT.
Autor: Florent Latifi · Mentore: Altina Salihu · Viti akademik 2023/2024 · Dorëzimi: 2026

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

Motori i refaktorimit aplikon dy transformime — Guard Clauses dhe Extract Method — dhe
i propozon tri të tjerat pa i aplikuar, sepse ato kërkojnë gjetjen e çdo reference në
projekt, çka analiza nuk e provon dot. **Refuzimi është rezultat i saktë** dhe raportohet
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
  api/         FastAPI
backend/tests/ Teste me vlera të derivuara me dorë
frontend/      React + TypeScript
docs/thesis/   Punimi sipas shabllonit të UBT-së
```

## Metrikat e implementuara

**Klasë:** CLOC, NOM, NOF, WMC, AMW, MAXCC, TCC, LCOM, LCOM\*, ATFD, CBO, RFC, WOC, NOPA, NOAM, DIT, NOC
**Metodë:** MLOC, CC, NP, MAXNESTING, ATFD, FDP, LAA, NOAV, CINT

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
| 2 | `build_dataset.py` | tabela e veçorive, e komituar | ~95 min |
| 3 | `evaluate_rules.py --from-dataset` | numrat e Qasjes A | sekonda |
| 4 | `train_models.py` | numrat e Qasjes B dhe modelet | sekonda |
| 5 | `sweep_thresholds.py` | analiza e ndjeshmërisë | sekonda |
| 6 | `evaluate_refactorings.py` | tabela N/M/K e Qasjes C | orë |
| 7 | `export_system_reference.py` | tabelat e Shtojcës (pragjet, strategjitë) | sekonda |
| 8 | `build_figures.py` | figurat e Kapitullit 5 | sekonda |
| 7 | `build_figures.py` | figurat e punimit | sekonda |

Hapi 2 është i vetmi kalim i shtrenjtë që duhet paguar: ai mat çdo entitet një herë,
dhe hapat 3 deri 5 lexojnë rreshtat e tij. Meqë tabela komitohet, një anëtar komisioni
me një checkout të pastër i riprodhon numrat pa korpusin 4.4 GB.

Hapat 2 dhe 6 shkruajnë në mënyrë inkrementale dhe rifillojnë aty ku mbetën.

## Referencat metodologjike

- Chidamber, S. R., Kemerer, C. F. (1994). *A Metrics Suite for Object Oriented Design.*
- Lanza, M., Marinescu, R. (2006). *Object-Oriented Metrics in Practice.*
- Fowler, M. (2018). *Refactoring: Improving the Design of Existing Code*, 2nd ed.
- Madeyski, L., Lewowski, T. (2020). *MLCQ: Industry-relevant code smell data set.*
