"""Verifikon që tabela e riprodhimit përshkruan skripte që i pranojnë ato komanda.

    python docs/thesis/check_reproduction.py

Shtojca e riprodhimit është premtimi qendror i punimit: një anëtar i komisionit me
një klon të pastër duhet t'i rigjenerojë numrat duke ndjekur atë tabelë rresht pas
rreshti. Premtimin nuk e mban asgjë në ndërtimin e dokumentit. Tabela është një
listë stringjesh te `chapters.py`, skriptet janë skedarë te `scripts/`, dhe të dyja
anët ndryshojnë veç e veç: një skript i riemërtuar, një skript i ri që askush nuk e
shtoi te tabela, ose një opsion i shtypur pa vlerën që ai kërkon nuk e prishin as
ndërtimin, as testet, as kontrollin e formatit. Prishin vetëm riprodhimin, dhe
vetëm te dikush që nuk mund ta raportojë më.

Kontrollohen tri gjëra:

**Që skripti ekziston.** Rreshti e emërton me shteg relativ ndaj `scripts/`.

**Që asnjë skript nuk mbetet jashtë.** Drejtimi i kundërt është ai që rrëshqet:
një eksperiment i ri prodhon një numër që hyn në Kapitullin 5, ndërsa tabela që
premton se numri riprodhohet nuk e përmend fare.

**Që komanda parsohet.** Opsionet e shtypura duhet të jenë opsione që skripti i
njeh, dhe një opsion që pret vlerë duhet ta ketë vlerën aty. Ky është i vetmi
kontroll që kërkon të lexohet vetë skripti, dhe lexohet si tekst me `ast`: importimi
i tyre do të sillte `javasmell`, `sklearn` dhe `matplotlib` në një punë CI-je që
instalon vetëm `python-docx`.

Del me kod jo-zero që kontrolli të mund të hyjë në CI bashkë me atë të citimeve.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from chapters import REPRODUCTION

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

#: Vetëm kjo nëndosje e `data/` është e komituar, ndaj vetëm për shtigjet brenda saj
#: mund të pretendohet se skedari gjendet te kloni i pastër që tabela presupozon.
COMMITTED = "data/results/"

#: Veprimet që e konsumojnë opsionin pa marrë vlerë pas tij. Çdo veprim tjetër,
#: përfshirë mungesën e tij, e bën opsionin të presë një vlerë.
VALUELESS = frozenset({"store_true", "store_false", "store_const", "count", "help", "version"})


def _options(path: Path) -> dict[str, bool]:
    """Opsionet e gjata që skripti deklaron, dhe nëse secili pret vlerë."""
    found: dict[str, bool] = {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords}
        action = keywords.get("action")
        valueless = isinstance(action, ast.Constant) and action.value in VALUELESS
        nargs = keywords.get("nargs")
        if isinstance(nargs, ast.Constant) and nargs.value == 0:
            valueless = True
        for argument in node.args:
            if isinstance(argument, ast.Constant) and str(argument.value).startswith("--"):
                found[str(argument.value)] = not valueless
    return found


def _check_command(command: str, root: Path) -> list[str]:
    """Një rresht i tabelës, i lexuar ashtu si do ta lexonte lexuesi: si komandë."""
    name, *arguments = command.split()
    script = SCRIPTS / name
    if not script.exists():
        return [f"rreshti «{command}» emërton {name}, që nuk gjendet te scripts/"]

    declared = _options(script)
    problems = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        index += 1
        if not token.startswith("--"):
            continue
        option, separator, inline = token.partition("=")
        if option not in declared:
            problems.append(f"{name} nuk e njeh opsionin {option}")
            continue
        if not declared[option] or separator:
            continue
        if index >= len(arguments) or arguments[index].startswith("--"):
            problems.append(f"{name} {option} pret një vlerë, e cila nuk është shtypur")
            continue
        value = arguments[index]
        index += 1
        if value.startswith(COMMITTED) and not (root / value).exists():
            problems.append(f"{name} {option} emërton {value}, që nuk është në depo")
    return problems


def report() -> list[str]:
    root = SCRIPTS.parent
    problems = []
    named = set()
    for _, command, _, _ in REPRODUCTION:
        named.add(command.split()[0])
        problems += _check_command(command, root)

    for script in sorted(SCRIPTS.glob("*.py")):
        if script.name not in named:
            problems.append(f"{script.name} nuk përmendet te tabela e riprodhimit")
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    problems = report()
    if not problems:
        print(f"Tabela e riprodhimit përputhet me scripts/: {len(REPRODUCTION)} hapa.")
        return 0
    print("Tabela e riprodhimit nuk përputhet me scripts/:")
    for problem in problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
