# scripts/

Pikënisjet e eksperimenteve. Çdo numër që përfundon në Kapitullin 5 duhet të
prodhohet nga një skript këtu, asnjë nga një sesion interaktiv, asnjë me kopjim
me dorë.

## Rregullat

1. **Një skript, një rezultat.** Emri e thotë çfarë prodhon:
   `evaluate_rules.py`, `train_classifier.py`, `sweep_thresholds.py`.
2. **Dalja shkon te `data/results/`** si CSV ose JSON, dhe **komitohet**. Ajo
   dosje është dëshmia; pjesa tjetër e `data/` është cache dhe injorohet.
3. **Farë e fiksuar** kudo ku ka rastësi, e deklaruar si konstante në krye.
4. **Idempotentë.** Ekzekutimi i dytë mbi të njëjtin input jep të njëjtin output.
   Puna e shtrenjtë (shkarkimi i korpusit) ruhet në cache dhe nuk përsëritet.
5. **Asnjë logjikë detektimi këtu.** Skriptet thërrasin `javasmell`; nëse një
   skript ka nevojë për logjikë të re analize, ajo i takon paketës.
6. **Mjedisi regjistrohet** në dalje: versioni i Python-it, versionet e paketave,
   commit-i i repos. Pa këtë, një rezultat nuk riprodhohet dot.

## Ekzekutimi

Nga rrënja e repos, me venv-in e aktivizuar:

```bash
python scripts/<emri>.py --help
```
