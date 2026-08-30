"""What the server is allowed to read, and how much of it.

Every limit here exists because a single HTTP request must not be able to
occupy the server indefinitely (ENGINEERING.md §6). They are configuration
rather than constants so that a run over a large corpus can raise them
deliberately, and so a test can lower them without rewriting the code it tests.

The root defaults to the working directory rather than to the filesystem root.
A tool that reads anything by default is a tool whose first misconfiguration is
also its last.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# A project of ten thousand files is a large one; past that the caller is almost
# certainly pointing at a directory they did not mean to.
DEFAULT_MAX_FILES = 10_000

# Two hundred megabytes of source is far more than any single analysis needs and
# still small enough to hold and measure.
DEFAULT_MAX_BYTES = 200_000_000

# Long enough for a real project, short enough that a pathological input cannot
# hold a worker forever.
DEFAULT_TIMEOUT_S = 300


@dataclass(frozen=True)
class Settings:
    """Where analysis may read, and the ceilings on one request."""

    root: Path
    max_files: int = DEFAULT_MAX_FILES
    max_bytes: int = DEFAULT_MAX_BYTES
    timeout_s: int = DEFAULT_TIMEOUT_S

    @classmethod
    def from_environment(cls) -> Settings:
        """Read the configuration, falling back to safe defaults.

        ``JAVASMELL_ROOT`` is the one setting a deployment must think about; the
        rest have defaults that only need changing for an unusual corpus.
        """
        return cls(
            root=Path(os.environ.get("JAVASMELL_ROOT", ".")).resolve(),
            max_files=int(os.environ.get("JAVASMELL_MAX_FILES", DEFAULT_MAX_FILES)),
            max_bytes=int(os.environ.get("JAVASMELL_MAX_BYTES", DEFAULT_MAX_BYTES)),
            timeout_s=int(os.environ.get("JAVASMELL_TIMEOUT_S", DEFAULT_TIMEOUT_S)),
        )
