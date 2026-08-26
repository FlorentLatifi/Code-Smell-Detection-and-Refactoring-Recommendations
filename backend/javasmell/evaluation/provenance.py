"""What a third party needs recorded in order to obtain a result again.

Every file under ``data/results/`` carries this block. It lives in the package
rather than in one of the scripts because the second script that needed it
would otherwise have copied it, and a copy is how the two LOC counters drifted
apart (VD-21).
"""

from __future__ import annotations

import platform
import subprocess

GIT_TIMEOUT_S = 10


def git_commit() -> str:
    """The revision the results were produced at, or "" outside a checkout."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip()


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": git_commit(),
    }
