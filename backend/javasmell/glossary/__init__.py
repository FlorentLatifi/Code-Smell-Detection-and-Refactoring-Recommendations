"""Fjalori i thjeshtë: çdo term teknik i mjetit, i shpjeguar për një lexues pa formim teknik.

Mjeti flet me emrat e literaturës: `FeatureEnvy`, `WOC < 0.333`, `ExtractMethod`,
`critical`. Ata janë të saktë dhe i lidhin gjetjet me burimin e tyre, por një
zhvillues që nuk e ka lexuar Lanza & Marinescu-n nuk merr vesh prej tyre çfarë nuk
shkon me kodin e vet. Ky fjalor i jep secilit term një emër shqip dhe një fjali që
e shpjegon, dhe për çdo erë edhe pse ka rëndësi dhe çfarë mund të bëhet (VD-144).

**Një skedar JSON, jo një modul Python.** E lexojnë dy anë: CLI-ja këtu dhe
ndërfaqja, që e importon drejtpërdrejt gjatë ndërtimit. Me dy kopje, një shpjegim do
të ndreqej te njëra dhe do të mbetej i vjetër te tjetra.

Fjalori nuk zëvendëson emrat teknikë: ata mbeten çelësat e të dhënave dhe shfaqen
në mënyrën teknike. Plotësia e tij kontrollohet nga testet, kundrejt erërave,
refaktorimeve dhe metrikave që prodhon vetë sistemi.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import TypedDict, cast


class Entry(TypedDict):
    """Një term: emri i thjeshtë dhe një fjali që e shpjegon."""

    name: str
    what: str


class SmellEntry(Entry):
    """Një erë, me arsyen pse ka rëndësi dhe çfarë mund të bëhet."""

    why: str
    fix: str


class Vocabulary(TypedDict):
    smells: dict[str, SmellEntry]
    smell_aliases: dict[str, str]
    metrics: dict[str, Entry]
    threshold_metrics: dict[str, str]
    severities: dict[str, Entry]
    refactorings: dict[str, Entry]
    operators: dict[str, str]
    terms: dict[str, Entry]


@cache
def vocabulary() -> Vocabulary:
    """I gjithë fjalori, i lexuar një herë."""
    text = resources.files(__package__).joinpath("plain_sq.json").read_text(encoding="utf-8")
    return cast(Vocabulary, json.loads(text))


def smell(name: str) -> SmellEntry | None:
    """Era sipas emrit të detektorit (`GodClass`) ose të MLCQ-së (`feature envy`)."""
    words = vocabulary()
    key = words["smell_aliases"].get(name.lower(), name)
    return words["smells"].get(key)


def metric(name: str) -> Entry | None:
    """Metrika sipas emrit, edhe me parashtesën e veçorive të modelit (`c_WMC`, `m_ATFD`)."""
    bare = name[2:] if name[:2] in ("c_", "m_") else name
    return vocabulary()["metrics"].get(bare)


def threshold_metric(name: str) -> Entry | None:
    """Metrika që kufizon një prag i emërtuar (`god_class_wmc` -> WMC).

    Pragjet kanë emrat e `Thresholds` dhe të skedarit TOML të `--thresholds`; një
    lexues i thjeshtë i njeh vetëm përmes metrikës që kufizojnë.
    """
    bare = vocabulary()["threshold_metrics"].get(name)
    return metric(bare) if bare else None


def severity(name: str) -> Entry | None:
    return vocabulary()["severities"].get(name)


def refactoring(name: str) -> Entry | None:
    return vocabulary()["refactorings"].get(name)


def reading(value: float) -> str:
    """Numri ashtu si lexohet: pa presje kur është i plotë, me tri shifra kur nuk është.

    TCC-ja vjen si 0.0183661 dhe pragu i saj si 0.333333; një lexues i krahason
    me tri shifra, dhe më shumë do të ishte zhurmë. E njëjta rregull përdoret te
    ndërfaqja.
    """
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def condition_sentence(metric_name: str, operator: str, threshold: float, value: float) -> str:
    """Një klauzolë si fjali: «Rreshtat e kodit të metodës: 77 (problem kur është mbi 35)».

    Kur metrika ose operatori nuk njihen, fjalia bie te emrat teknikë në vend që të
    shpikë një shpjegim: një term i panjohur duhet të shihet, jo të fshihet.
    """
    entry = metric(metric_name)
    name = entry["name"] if entry else metric_name
    word = vocabulary()["operators"].get(operator, operator)
    return f"{name}: {reading(value)} (problem kur është {word} {reading(threshold)})"
