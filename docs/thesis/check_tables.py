"""Kontrollon që tabelat e punimit të jenë konsistente me njëra-tjetrën.

    python docs/thesis/check_tables.py [shtegu.docx]

Mentorja kërkoi që të rishikohej «konsistenca e të dhënave dhe rezultateve të
paraqitura në tabela» (VD-150). Çdo tabelë lexohet nga një skedar rezultati, por
asgjë nuk provonte që tabela të ndryshme thonë të njëjtën gjë kur flasin për të
njëjtin numër: që pjesët mblidhen te totali, që përmbledhja e 5.8 përsërit vlerat e
5.1 dhe 5.2, që tabela sipas transformimit mblidhet te tabela e motorit. Kontrolli
lexon dokumentin e ndërtuar, jo burimet, sepse lexuesi sheh dokumentin.

Tabelat gjenden sipas titullit, jo sipas numrit, që një tabelë e re të mos e
zhvendosë kontrollin. Një tabelë që mungon raportohet si gabim: heshtja do të
dukej si konsistencë.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from build_thesis import OUTPUT
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

CAPTION = re.compile(r"^Tabela \d+\. (.+)$")


def tables_by_title(path: Path) -> dict[str, list[list[str]]]:
    """Çdo tabelë e dokumentit, sipas titullit që e paraprin."""
    document = Document(str(path))
    found: dict[str, list[list[str]]] = {}
    title = None
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            match = CAPTION.match(Paragraph(child, document).text.strip())
            title = match.group(1) if match else title
        elif tag == "tbl" and title is not None:
            rows = [[cell.text.strip() for cell in row.cells] for row in Table(child, document).rows]
            found[title] = rows
            title = None
    return found


def number(cell: str) -> float:
    """Numri i parë i një qelize: «3532», «3298 (93.4%)», «15 800», «0.232»."""
    # Mijëshet ndahen me hapësirë të pandashme (`_count` te chapters.py).
    cell = cell.replace(" ", " ").replace(" ", " ")
    match = re.search(r"-?\d[\d ]*(?:\.\d+)?", cell)
    if match is None:
        raise ValueError(f"asnjë numër te «{cell}»")
    return float(match.group(0).replace(" ", ""))


def band(cell: str) -> tuple[float, float]:
    low, high = (float(x) for x in re.findall(r"-?\d+\.\d+", cell)[:2])
    return low, high


def check(tables: dict[str, list[list[str]]]) -> list[str]:
    problems: list[str] = []

    def need(title: str) -> list[list[str]] | None:
        if title not in tables:
            problems.append(f"mungon tabela «{title}»")
            return None
        return tables[title]

    def expect(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    engine = need("Rezultati i motorit të refaktorimit")
    refused = need("Pse u refuzuan")
    verdicts = need("Verifikimi i atyre që u aplikuan")
    resolution = need("A u hoq era pas rishkrimit")
    by_transformation = need("Rezultati i refaktorimit sipas transformimit")
    by_severity = need("Norma e transformimit sipas erës dhe ashpërsisë")

    if engine:
        totals = {row[0]: number(row[1]) for row in engine[1:]}
        detected = totals["Vende të detektuara"]
        applied = totals["Të transformuara"]
        parts = sum(value for name, value in totals.items() if name != "Vende të detektuara")
        expect(parts == detected, f"motori: pjesët japin {parts:g}, jo {detected:g} vende")
        if refused:
            expect(
                sum(number(r[1]) for r in refused[1:]) == totals["Të refuzuara"],
                "refuzimet sipas arsyes nuk mblidhen te të refuzuarat",
            )
        if verdicts:
            expect(
                sum(number(r[1]) for r in verdicts[1:]) == applied,
                "verdiktet nuk mblidhen te të transformuarat",
            )
        if resolution:
            expect(
                sum(number(r[1]) for r in resolution[1:]) == applied,
                "rezultatet e rimatjes nuk mblidhen te të transformuarat",
            )
        if by_transformation:
            sites = sum(number(r[1]) for r in by_transformation[1:])
            located = detected - totals.get("Të palokalizueshme", 0)
            expect(sites == located, f"sipas transformimit: {sites:g} vende, jo {located:g}")
            expect(
                sum(number(r[2]) for r in by_transformation[1:]) == applied,
                "sipas transformimit: të transformuarat nuk mblidhen te totali",
            )
            if verdicts:
                clean = sum(
                    number(r[1]) for r in verdicts[1:] if r[0] in ("kompilon", "pa gabim të ri")
                )
                expect(
                    sum(number(r[3]) for r in by_transformation[1:]) == clean,
                    "sipas transformimit: «pa gabim të ri» nuk përkon me verdiktet",
                )
            if resolution:
                removed = next(number(r[1]) for r in resolution[1:] if r[0] == "era u hoq")
                expect(
                    sum(number(r[4]) for r in by_transformation[1:]) == removed,
                    "sipas transformimit: «era u hoq» nuk përkon me rimatjen",
                )
        if by_severity:
            expect(
                sum(number(r[3]) for r in by_severity[1:]) == applied,
                "norma sipas ashpërsisë: të transformuarat nuk mblidhen te totali",
            )
            expect(
                sum(number(r[2]) for r in by_severity[1:]) == detected - totals.get("Të palokalizueshme", 0),
                "norma sipas ashpërsisë: vendet e gjykuara nuk mblidhen te totali",
            )

    rules = need("Qasja A kundrejt gjykimit të rishikuesve")
    models = need("Modeli më i mirë për çdo erë")
    summary = need("Shifrat kryesore sipas pyetjes kërkimore")
    intervals = need("Intervale besimi 95% për MCC-në")
    agreement = need("Pajtimi mes dy qasjeve")
    severity = need("Recall-i sipas ashpërsisë")
    literature = need("Krahasimi i MCC-së me Madeyski dhe Lewowski (2023), mbi MLCQ")
    combined = need("Të dyja qasjet së bashku")

    strategy = {r[0]: r for r in rules[1:] if "(+" not in r[0]} if rules else {}
    best = {r[0]: r for r in models[1:]} if models else {}

    if summary and strategy and best:
        by_name = {r[1]: r[2] for r in summary[1:]}

        def same_band(label: str, values: list[float]) -> None:
            low, high = band(by_name.get(label, "0.0 0.0"))
            expect(
                (low, high) == (min(values), max(values)),
                f"5.8 «{label}» {low}–{high} nuk përkon me tabelat e burimit "
                f"{min(values)}–{max(values)}",
            )

        same_band("MCC e strategjive", [number(r[4]) for r in strategy.values()])
        same_band("Precizioni i strategjive", [number(r[1]) for r in strategy.values()])
        same_band("Recall-i i strategjive", [number(r[2]) for r in strategy.values()])
        same_band("MCC e modelit më të mirë", [number(r[5]) for r in best.values()])

    if literature and strategy and best:
        for row in literature[1:]:
            expect(
                number(row[1]) == number(strategy[row[0]][4]),
                f"6.3: MCC e Qasjes A te {row[0]} nuk përkon me 5.1",
            )
            expect(
                number(row[2]) == number(best[row[0]][5]),
                f"6.3: MCC e Qasjes B te {row[0]} nuk përkon me 5.2",
            )

    if combined and best:
        for row in combined[1:]:
            expect(
                number(row[1]) == number(best[row[0]][5]),
                f"5.3: MCC e modelit te {row[0]} nuk përkon me tabelën e modeleve",
            )

    if intervals and strategy and best:
        for row in intervals[1:]:
            a_low, a_high = band(row[1])
            b_low, b_high = band(row[2])
            a, b = number(strategy[row[0]][4]), number(best[row[0]][5])
            expect(a_low <= a <= a_high, f"5.7: MCC e A te {row[0]} jashtë intervalit të vet")
            expect(b_low <= b <= b_high, f"5.7: MCC e B te {row[0]} jashtë intervalit të vet")

    if agreement and rules:
        positives = {r[0]: number(r[5]) for r in strategy.values()}
        for row in agreement[1:]:
            both, only_a, only_b, n = (number(x) for x in row[2:6])
            expect(both + only_a + only_b <= n, f"5.3: te {row[0]} të shënuarat kalojnë n-në")
            expect(positives[row[0]] <= n, f"5.1: te {row[0]} pozitivët kalojnë mostrat")

    if severity and rules:
        all_rules = {r[0]: number(r[5]) for r in rules[1:]}
        for row in severity[1:]:
            supported = sum(number(cell.split("/")[1]) for cell in row[1:3])
            expect(
                supported <= all_rules[row[0]],
                f"5.1: te {row[0]} rastet major dhe minor kalojnë pozitivët",
            )

    quality = need("Pranueshmëria e rishkrimeve sipas rishikuesit")
    if quality:
        for row in quality[1:]:
            parts = number(row[2]) + number(row[3]) + number(row[4])
            expect(parts == number(row[1]), f"5.4: te {row[0]} gjykimet nuk mblidhen te të lexuarat")

    isolated = need("Verdikti i të njëjtave rishkrime, të izoluara dhe brenda projektit")
    if isolated:
        alone = sum(number(r[1]) for r in isolated[1:])
        within = sum(number(r[2]) for r in isolated[1:])
        expect(alone == within, f"5.4: kolonat e verifikimit brenda projektit japin {alone:g} dhe {within:g}")

    return problems


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(OUTPUT)
    found = check(tables_by_title(path))
    if found:
        print("Tabelat nuk përputhen:")
        print("\n".join(f"  {item}" for item in found))
        sys.exit(1)
    print(f"Tabelat përputhen me njëra-tjetrën: {path.name}")
