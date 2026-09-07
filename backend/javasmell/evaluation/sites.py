"""Where in a file the engine has something to rewrite, in a fixed order.

This walk decides the order of the rows in ``refactoring_sites.csv``, and that
file carries no line number, so the position of a row inside its file is the
only unambiguous way back to the site it describes when a class overloads a
method (the gap VD-55 ran into). Anything that wants to reopen a recorded site
has to reproduce this order exactly.

It lives here rather than in the script that first needed it for that reason.
A second copy would be correct on the day it was made and wrong the first time
either changed, and the two LOC counters that drifted apart (VD-21) are what
that looks like afterwards.
"""

from __future__ import annotations

from javasmell.analysis import analyze_source
from javasmell.detectors.rules import detect_in_class
from javasmell.refactor.registry import for_smell

#: (class, method, smell, refactoring, line) for one automatable site.
Site = tuple[str, str, str, str, int]


def sites_in(source: bytes, path: str) -> list[Site]:
    """Every smell the engine automates, in the order the walk finds them."""
    try:
        project = analyze_source(source.decode("utf-8"), path)
    except (UnicodeDecodeError, ValueError):
        return []

    found: list[Site] = []
    for unit in project.units:
        for cls in unit.classes:
            for smell in detect_in_class(cls):
                automated = for_smell(smell.smell_type)
                if automated is None or smell.method is None:
                    continue
                name = smell.method.partition("(")[0]
                found.append((cls.name, name, smell.smell_type, automated[0], smell.start_line))
    return found
