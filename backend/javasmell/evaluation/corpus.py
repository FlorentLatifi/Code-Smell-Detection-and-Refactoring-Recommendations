"""Layout of the local MLCQ corpus, and the record of what could be fetched.

Separated from the download script because two very different things need this
knowledge: the fetcher, which writes the tree, and the evaluation harness,
which reads it months later. Keeping the layout in one place means a rename
cannot leave the two disagreeing silently.

The manifest is not bookkeeping for its own sake. Some of MLCQ's 522 published
repositories no longer resolve (deleted, renamed, or made private since 2020),
and the fraction that could not be retrieved is a stated limitation of the
study, so it has to be recorded as it happens rather than reconstructed later.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from javasmell.evaluation.mlcq import Sample

MANIFEST_NAME = "manifest.json"

# Enough of the commit to be unique in practice while keeping directory names
# readable; the full hash is preserved in the manifest.
SHORT_HASH = 12

WINDOWS_LONG_PATH_PREFIX = "\\\\?\\"


def long_path(path: Path) -> Path:
    """Return a form of ``path`` that Windows will accept at any depth.

    Windows refuses paths beyond 260 characters unless the extended-length
    prefix is used, and this corpus exceeds that routinely: Java package trees
    inside the analysed projects reach 174 characters on their own, on top of
    whatever the checkout root costs. The failure mode is quiet and misleading
    -- ``FileNotFoundError`` on a file that is plainly there, or ``is_file()``
    simply returning False, so every filesystem access below the corpus root
    goes through here.

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


@dataclass
class RepoStatus:
    """The outcome of trying to materialise one repository."""

    repository: str
    commit_hash: str
    directory: str
    ok: bool
    java_files: int = 0
    bytes_written: int = 0
    reason: str = ""  # why it failed, empty when ok


@dataclass
class Manifest:
    """Everything the fetcher learned, in a form the harness can trust."""

    entries: dict[str, RepoStatus] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> Manifest:
        path = root / MANIFEST_NAME
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(entries={k: RepoStatus(**v) for k, v in raw.items()})

    def save(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        payload = {k: asdict(v) for k, v in sorted(self.entries.items())}
        (root / MANIFEST_NAME).write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def record(self, status: RepoStatus) -> None:
        self.entries[status.repository] = status

    def is_done(self, repository: str) -> bool:
        """A repository is done only if it succeeded.

        Failures are deliberately retried on the next run: a network timeout is
        transient, and treating it as final would quietly shrink the corpus.
        """
        entry = self.entries.get(repository)
        return entry is not None and entry.ok


def repo_dirname(sample: Sample) -> str:
    """A filesystem-safe, collision-free directory name for one checkout."""
    owner, name = sample.owner_and_name
    return f"{owner}__{name}__{sample.commit_hash[:SHORT_HASH]}"


class Corpus:
    """The on-disk corpus rooted at ``root``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def repo_dir(self, sample: Sample) -> Path:
        return self.root / repo_dirname(sample)

    def source_path(self, sample: Sample) -> Path:
        """Where the file holding this sample should be, if it was fetched.

        ``Sample.path`` is published with a leading slash. Joining it directly
        would produce an absolute path and escape the corpus root entirely, so
        the relative form is used and the result is confined below the root.
        """
        candidate = (self.repo_dir(sample) / sample.relative_path).resolve()
        root = self.root.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"sample path escapes the corpus root: {sample.path!r}")
        return candidate

    def has_source(self, sample: Sample) -> bool:
        try:
            return long_path(self.source_path(sample)).is_file()
        except ValueError:
            return False

    def analysable_root(self, sample: Sample) -> str:
        """The checkout root in the form the analyser must be handed.

        ``iter_java_files`` walks this tree, and on Windows that walk stops
        dead at the path limit unless the root already carries the prefix.
        """
        return str(long_path(self.repo_dir(sample)))

    def coverage(self, samples: Iterable[Sample]) -> Coverage:
        """How much of the ground truth this corpus can actually be used with."""
        total = 0
        available = 0
        repos: set[str] = set()
        repos_available: set[str] = set()
        for sample in samples:
            total += 1
            repos.add(sample.repository)
            if self.has_source(sample):
                available += 1
                repos_available.add(sample.repository)
        return Coverage(
            samples_total=total,
            samples_available=available,
            repositories_total=len(repos),
            repositories_available=len(repos_available),
        )


@dataclass(frozen=True)
class Coverage:
    """The number that goes into the thesis as a limitation."""

    samples_total: int
    samples_available: int
    repositories_total: int
    repositories_available: int

    @property
    def sample_fraction(self) -> float:
        return self.samples_available / self.samples_total if self.samples_total else 0.0

    @property
    def repository_fraction(self) -> float:
        if not self.repositories_total:
            return 0.0
        return self.repositories_available / self.repositories_total

    def describe(self) -> str:
        return (
            f"{self.samples_available}/{self.samples_total} samples "
            f"({self.sample_fraction:.1%}) from "
            f"{self.repositories_available}/{self.repositories_total} repositories "
            f"({self.repository_fraction:.1%})"
        )
