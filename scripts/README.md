# scripts/

Pikënisjet e eksperimenteve. Çdo numër që përfundon në Kapitullin 5 duhet të
prodhohet nga një skript këtu, asnjë nga një sesion interaktiv, asnjë me kopjim
me dorë.

## Rregullat

1. **Një skript, një rezultat.** Emri e thotë çfarë prodhon:
   `evaluate_rules.py`, `train_models.py`, `sweep_thresholds.py`.
2. **Dalja shkon te `data/results/`** si CSV ose JSON, dhe **komitohet**. Ajo
   dosje është dëshmia; pjesa tjetër e `data/` është cache dhe injorohet.
3. **Farë e fiksuar** kudo ku ka rastësi, e deklaruar si konstante në krye.
4. **Idempotentë.** Ekzekutimi i dytë mbi të njëjtin input jep të njëjtin output.
   Puna e shtrenjtë (shkarkimi i korpusit) ruhet në cache dhe nuk përsëritet.
5. **Asnjë logjikë detektimi këtu.** Skriptet thërrasin `javasmell`; nëse një
   skript ka nevojë për logjikë të re analize, ajo i takon paketës.
6. **Mjedisi regjistrohet** në dalje: versioni i Python-it, versionet e paketave,
   commit-i i repos. Pa këtë, një rezultat nuk riprodhohet dot.

## Radha

Skriptet varen nga njëri-tjetri në këtë radhë. Koha është për një laptop pa GPU.

| # | Skripti | Prodhon | Kohë |
|---|---|---|---|
| 1 | `fetch_corpus.py` | `data/corpus/` (4.4 GB, jashtë git-it) | orë, një herë |
| 2 | `report_matching.py` | `mlcq_matching.json` | ~2 min |
| 3 | `build_dataset.py` | `mlcq_dataset.csv` | **~95 min** |
| 4 | `evaluate_rules.py` | `rules_evaluation.json` | ~95 min |
| 5 | `train_models.py` | `ml_evaluation.json`, `data/models/` | sekonda |
| 6 | `sweep_thresholds.py` | `threshold_sweep.json` | sekonda |
| 7 | `evaluate_refactorings.py` | `refactoring_evaluation.json`, `refactoring_sites.csv` | **orë** |
| 8 | `calibrate_thresholds.py` | `threshold_calibration.json` | ~1 min |
| 9 | `reviewer_agreement.py` | `reviewer_agreement.json` | sekonda |
| 10 | `bootstrap_intervals.py` | `bootstrap_intervals.json` | nën një minutë |
| 11 | `refusals_by_severity.py` | `refusals_by_severity.json` | minuta |
| 12 | `verify_with_project.py` | `verify_with_project.json` | ~18 min (mostër) |
| 13 | `model_without_project.py` | `model_without_project.json` | minuta |
| 14 | `export_system_reference.py` | `system_reference.json` | sekonda |
| 15 | `build_figures.py` | figurat e Kapitullit 5 | sekonda |

Hapat 1, 3, 4 dhe 7 janë të vetmit që kushtojnë vërtet. Hapat 11–13 nuk kërkojnë
`javac` përveç hapit 12, i cili e ekzekuton atë një herë për çdo rishkrim dhe
prandaj punon mbi një mostër me farë të fiksuar.

Hapi 3 është kalimi i vetëm i shtrenjtë që duhet paguar (VD-23): ai mat çdo entitet
të mostruar një herë, dhe gjithçka pas tij lexon rreshtat e tij. Meqë `mlcq_dataset.csv`
komitohet, një anëtar komisioni me një checkout të pastër i riprodhon numrat e hapit
5 pa korpusin dhe pa 95 minutat.

Hapi 4 ende e bën kalimin e vet; kalimi i tij te tabela e veçorive është punë e
mbetur, e mundur sepse rreshti mban edhe `kind`, `is_constructor` e `is_accessor`,
të vetmet fusha jo-metrike që rregullat lexojnë.

## Ekzekutimi

Nga rrënja e repos, me venv-in e aktivizuar:

```bash
python scripts/<emri>.py --help
```
