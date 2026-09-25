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


def javac_version() -> str:
    """The compiler behind a compile verdict, or "" when javac could not be asked.

    "It compiles" is a statement about a compiler as much as about the code: a
    file one release accepts, the next can reject. The two measurements that run
    javac therefore record which one answered, so a reader who obtains different
    counts can see whether they even compared the same compiler (VD-136).
    """
    try:
        completed = subprocess.run(
            ["javac", "-version"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    # Up to JDK 8 the version went to stderr, from JDK 9 to stdout.
    reported = completed.stdout.strip() or completed.stderr.strip()
    return reported.splitlines()[0].strip() if reported else ""


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": git_commit(),
    }
