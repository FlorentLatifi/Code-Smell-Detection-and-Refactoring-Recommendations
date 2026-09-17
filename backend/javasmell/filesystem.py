"""Filesystem facts that hold for every layer, starting with Windows path length.

One module rather than a helper inside the corpus, because two unrelated parts
of the system now write deep trees: the corpus fetcher and the GitHub import
that the web interface offers. Two copies of the extended-length prefix rule
would be two things to get right, and the failure mode is silent (VD-126).
"""

from __future__ import annotations

import os
from pathlib import Path

WINDOWS_LONG_PATH_PREFIX = "\\\\?\\"


def long_path(path: Path) -> Path:
    """Return a form of ``path`` that Windows will accept at any depth.

    Windows refuses paths beyond 260 characters unless the extended-length
    prefix is used, and a real Java repository exceeds that routinely: package
    trees inside the analysed projects reach 174 characters on their own, on top
    of whatever the checkout root costs. The failure mode is quiet and
    misleading -- ``FileNotFoundError`` on a file that is plainly there, or
    ``is_file()`` simply returning False, so every filesystem access below such
    a root goes through here.

    Lifting the limit system-wide instead would need administrator rights and
    would make the corpus reproducible only on a machine configured that way,
    which defeats the point of a corpus a third party can rebuild.
    """
    if os.name != "nt":
        return path
    resolved = path.resolve()
    if str(resolved).startswith(WINDOWS_LONG_PATH_PREFIX):
        return resolved
    return Path(WINDOWS_LONG_PATH_PREFIX + str(resolved))
