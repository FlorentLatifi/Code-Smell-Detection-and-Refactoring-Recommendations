# Code Smell Detection and Refactoring Recommendations

Punim diplome — Bachelor, Shkenca Kompjuterike dhe Inxhinieri, UBT.
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

```bash
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
```

```bash
.venv/Scripts/python -m pytest backend -q
```

## Referencat metodologjike

- Chidamber, S. R., Kemerer, C. F. (1994). *A Metrics Suite for Object Oriented Design.*
- Lanza, M., Marinescu, R. (2006). *Object-Oriented Metrics in Practice.*
- Fowler, M. (2018). *Refactoring: Improving the Design of Existing Code*, 2nd ed.
- Madeyski, L., Lewowski, T. (2020). *MLCQ: Industry-relevant code smell data set.*
